import trio
import logging
import time

try:
    from pycaster.tokens import prepare_tokens, match_token
    from pycaster.protocol import parse_request
except ImportError:
    # If running directly, try relative imports
    from tokens import prepare_tokens, match_token
    from protocol import parse_request


async def send_source_table(stream, sources, lock):
    """Send NTRIP source table to client."""
    async with lock:
        active_sources = list(sources.keys())
    
    # Build the table content first, matching the C implementation format
    table_content = ""
    for mount in active_sources:
        # Format matching the C code: STR;mount;mount;RTCM3X;1005(10),1074-1084-1124(1);2;GNSS;NET;CL;0.00;0.00;1;1;None;None;B;N;0;
        table_content += f"STR;{mount};{mount};RTCM3X;1005(10),1074-1084-1124(1);2;GNSS;NET;CL;0.00;0.00;1;1;None;None;B;N;0;\r\n"
    
    table_content += "ENDSOURCETABLE\r\n"
    
    # Build the NTRIP response (not HTTP), matching the C implementation
    import time
    from datetime import datetime
    
    now = datetime.utcnow()
    timestr = now.strftime("%a %b %d %H:%M:%S %Y")
    content_length = len(table_content.encode('utf-8'))
    
    response = f"SOURCETABLE 200 OK\r\n"
    response += f"Server: https://github.com/tisyang/ntripcaster.git\r\n"
    response += f"Date: {timestr} UTC\r\n"
    response += f"Connection: close\r\n"
    response += f"Content-Type: text/plain\r\n"
    response += f"Content-Length: {content_length}\r\n"
    response += f"\r\n"
    response += table_content
    
    await stream.send_all(response.encode('utf-8'))


async def timeout_monitor(clients, sources, client_stats, source_stats, lock, interval=10, timeout=60):
    """Monitor connections for timeouts and log statistics"""
    while True:
        await trio.sleep(interval)
        now = time.time()
        
        async with lock:
            # Check and remove inactive connections
            logging.debug("======= Current clients/servers status ========")
            logging.debug("%-8s %-8s %-16s %-5s %-8s %s", "Type", "MountP", "From", "Bps", "Bytes", "UserAgent")
            
            # Check clients for timeout
            clients_to_remove = []
            for mount, client_set in clients.items():
                clients_in_mount_to_remove = []
                for client in list(client_set):
                    if client in client_stats:
                        stats = client_stats[client]
                        # Log client statistics
                        logging.debug("%-8s %-8s %-16s %-5d %-8d %s", 
                                    "Client", mount, str(stats['addr']), 
                                    stats['out_bps'], stats['out_bytes'], 
                                    stats.get('user_agent', ''))
                        
                        # Check for timeout
                        if now - stats['last_activity'] >= timeout:
                            logging.info("Timeout client on mount %s from %s", mount, stats['addr'])
                            clients_in_mount_to_remove.append(client)
                            try:
                                await client.aclose()
                            except:
                                pass
                
                # Remove timed out clients
                for client in clients_in_mount_to_remove:
                    client_set.discard(client)
                    client_stats.pop(client, None)
                
                # Remove empty mount points
                if not client_set:
                    clients_to_remove.append(mount)
            
            for mount in clients_to_remove:
                clients.pop(mount, None)
            
            # Check sources for timeout
            sources_to_remove = []
            for mount, source in list(sources.items()):
                if source in source_stats:
                    stats = source_stats[source]
                    # Log source statistics
                    logging.debug("%-8s %-8s %-16s %-5d %-8d %s", 
                                "Source", mount, str(stats['addr']), 
                                stats['in_bps'], stats['in_bytes'], 
                                stats.get('user_agent', ''))
                    
                    # Check for timeout
                    if now - stats['last_activity'] >= timeout:
                        logging.info("Timeout source on mount %s from %s", mount, stats['addr'])
                        sources_to_remove.append(mount)
                        try:
                            await source.aclose()
                        except:
                            pass
            
            # Remove timed out sources
            for mount in sources_to_remove:
                if mount in sources:
                    source = sources[mount]
                    sources.pop(mount, None)
                    source_stats.pop(source, None)
            
            logging.debug("-----------------------------------------------")
            
            # Reset BPS counters (they represent current activity)
            for stats in client_stats.values():
                stats['out_bps'] = 0
            for stats in source_stats.values():
                stats['in_bps'] = 0


async def handle_agent(stream, cfg, client_tokens, source_tokens, clients, sources, client_stats, source_stats, lock):
    addr = stream.socket.getpeername()
    logging.info("Connection from %s", addr)
    
    # Get client disconnect delay from config (default 5 seconds)
    client_disconnect_delay = cfg.get('client_disconnect_delay', 5)
    
    data = b''
    try:
        while b'\r\n\r\n' not in data:
            chunk = await stream.receive_some(1024)
            if not chunk:
                logging.info("Connection closed before headers from %s", addr)
                return
            data += chunk
            if len(data) > 4096:
                logging.warning("Header too large from %s", addr)
                return
    except (trio.BrokenResourceError, trio.ClosedResourceError, ConnectionResetError, OSError) as e:
        logging.debug("Connection lost during header reading from %s: %s", addr, e)
        return
    except Exception as e:
        logging.warning("Error reading headers from %s: %s", addr, e)
        return
    req = parse_request(data)
    if not req:
        logging.warning("Malformed request from %s", addr)
        await stream.aclose()
        return
    mount = req['mountpoint']
    if req['type'] == 'client':
        # Check if the requested mountpoint exists
        async with lock:
            has_mountpoint = mount and mount in sources
        
        # If no mountpoint specified, empty, root path, or mountpoint doesn't exist, send source table
        if not mount or mount == '' or mount == '/' or not has_mountpoint:
            logging.info("Client requesting source table from %s (mountpoint: '%s')", addr, mount)
            await send_source_table(stream, sources, lock)
            await stream.aclose()
            return
        
        token = req['auth'].split()[-1] if req['auth'] else ''
        if not match_token(client_tokens, token, mount):
            logging.warning("Client auth failed for mount %s from %s", mount, addr)
            await stream.send_all(b"HTTP/1.0 401 Unauthorized\r\n\r\n")
            await stream.aclose()
            return
        
        # Initialize client statistics
        now = time.time()
        client_stat = {
            'addr': addr,
            'user_agent': req.get('user_agent', ''),
            'login_time': now,
            'last_activity': now,
            'out_bytes': 0,
            'out_bps': 0
        }
        
        async with lock:
            clients.setdefault(mount, set()).add(stream)
            client_stats[stream] = client_stat
        
        await stream.send_all(b"ICY 200 OK\r\n")
        logging.info("Client connected to %s from %s", mount, addr)
        try:
            while True:
                try:
                    data = await stream.receive_some(1024)
                    if not data:
                        break
                    # Update activity timestamp
                    async with lock:
                        if stream in client_stats:
                            client_stats[stream]['last_activity'] = time.time()
                except trio.ClosedResourceError:
                    # Connection was closed, break the loop
                    break
                except Exception as e:
                    logging.warning("Error reading from client %s on mount %s: %s", addr, mount, e)
                    break
        finally:
            async with lock:
                if mount in clients:
                    clients[mount].discard(stream)
                    if not clients[mount]:  # Remove empty mountpoint
                        clients.pop(mount, None)
                client_stats.pop(stream, None)
            await stream.aclose()
        logging.info("Client disconnected from %s (%s)", mount, addr)
    elif req['type'] == 'source':
        if not match_token(source_tokens, req['passwd'], mount):
            logging.warning("Source auth failed for mount %s from %s", mount, addr)
            await stream.send_all(b"ERROR - Bad Password\r\n")
            await stream.aclose()
            return
        async with lock:
            if mount in sources:
                logging.warning("Mountpoint %s already in use from %s", mount, addr)
                await stream.send_all(b"ERROR - Bad Mountpoint\r\n")
                await stream.aclose()
                return
            sources[mount] = stream
        
        # Initialize source statistics
        now = time.time()
        source_stat = {
            'addr': addr,
            'user_agent': req.get('user_agent', ''),
            'login_time': now,
            'last_activity': now,
            'in_bytes': 0,
            'in_bps': 0
        }
        
        async with lock:
            source_stats[stream] = source_stat
        
        await stream.send_all(b"ICY 200 OK\r\n")
        logging.info("Source connected to %s from %s", mount, addr)
        try:
            while True:
                try:
                    data = await stream.receive_some(8192)
                    if not data:
                        break
                    
                    # Update source statistics
                    data_len = len(data)
                    async with lock:
                        if stream in source_stats:
                            source_stats[stream]['last_activity'] = time.time()
                            source_stats[stream]['in_bytes'] += data_len
                            source_stats[stream]['in_bps'] = data_len * 8
                        
                        # Send data to clients and update their statistics
                        for client in list(clients.get(mount, [])):
                            try:
                                await client.send_all(data)
                                if client in client_stats:
                                    client_stats[client]['last_activity'] = time.time()
                                    client_stats[client]['out_bytes'] += data_len
                                    client_stats[client]['out_bps'] = data_len * 8
                            except Exception:
                                clients[mount].discard(client)
                                client_stats.pop(client, None)
                except (trio.BrokenResourceError, trio.ClosedResourceError, ConnectionResetError, OSError) as e:
                    logging.info("Source connection lost from %s (%s): %s", mount, addr, e)
                    break
                except Exception as e:
                    logging.warning("Unexpected error reading from source %s (%s): %s", mount, addr, e)
                    break
        finally:
            async with lock:
                sources.pop(mount, None)
                source_stats.pop(stream, None)
                
                # Get clients connected to this mountpoint but don't remove them yet
                clients_to_close = list(clients.get(mount, []))
                
            await stream.aclose()
            
            # Wait a few seconds before closing clients in case source reconnects quickly
            if clients_to_close:
                logging.info("Source disconnected from %s (%s), waiting %d seconds before closing %d clients", 
                           mount, addr, client_disconnect_delay, len(clients_to_close))
                await trio.sleep(client_disconnect_delay)
                
                # Check if source reconnected during the wait
                async with lock:
                    if mount in sources:
                        # Source reconnected, don't close clients
                        logging.info("Source reconnected to %s, keeping clients connected", mount)
                        return
                    
                    # Source didn't reconnect, close clients
                    clients.pop(mount, None)
                
                # Close clients outside the lock to avoid blocking
                for client in clients_to_close:
                    try:
                        await client.aclose()
                        client_stats.pop(client, None)
                    except:
                        pass
                        
                logging.info("Closed %d clients for disconnected source %s", len(clients_to_close), mount)
            else:
                logging.info("Source disconnected from %s (%s)", mount, addr)


async def run_server(cfg):
    client_tokens = prepare_tokens(cfg['tokens_client'])
    source_tokens = cfg['tokens_source']
    clients = {}
    sources = {}
    client_stats = {}  # Track client connection statistics
    source_stats = {}  # Track source connection statistics
    pending_connections = 0  # Track pending (unidentified) connections
    lock = trio.Lock()
    listeners = await trio.open_tcp_listeners(cfg['listen_port'], host=cfg['listen_addr'])
    logging.info('Listening on %s:%s', cfg['listen_addr'], cfg['listen_port'])
    async with trio.open_nursery() as nursery:
        # Start the timeout monitor
        nursery.start_soon(timeout_monitor, clients, sources, client_stats, source_stats, lock)
        
        async def handle_connection(stream):
            nonlocal pending_connections
            
            # Increment pending connections count
            async with lock:
                pending_connections += 1
                current_pending = pending_connections
            
            # Check max_pending limit
            max_pending = cfg.get('max_pending', 10)
            if max_pending > 0 and current_pending > max_pending:
                try:
                    addr = stream.socket.getpeername()
                    logging.warning("Too many pending connections (%d), rejecting connection from %s", current_pending, addr)
                except:
                    logging.warning("Too many pending connections (%d), rejecting connection", current_pending)
                async with lock:
                    pending_connections -= 1
                await stream.aclose()
                return
            
            try:
                await handle_agent(stream, cfg, client_tokens, source_tokens, 
                                 clients, sources, client_stats, source_stats, lock)
            except (trio.BrokenResourceError, trio.ClosedResourceError, ConnectionResetError, OSError) as e:
                try:
                    addr = stream.socket.getpeername()
                    logging.debug("Connection error from %s: %s", addr, e)
                except:
                    logging.debug("Connection error: %s", e)
            except Exception as e:
                try:
                    addr = stream.socket.getpeername()
                    logging.error("Unexpected error handling connection from %s: %s", addr, e)
                except:
                    logging.error("Unexpected error handling connection: %s", e)
            finally:
                # Decrement pending connections count when connection ends
                async with lock:
                    if pending_connections > 0:
                        pending_connections -= 1
        
        for lst in listeners:
            nursery.start_soon(trio.serve_listeners, handle_connection, [lst])
