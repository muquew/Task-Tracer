# Session proxy transport control

This is a transport-method validation, not an application acceptance result. It read a cache-busted public HTTPS manifest only, without loading application HTML, service workers, task data or local application source. Normal WebKit TLS verification remained enabled.

The local relay forwards opaque TCP bytes only to the inherited HTTP session proxy. It does not connect directly to the requested destination, decrypt TLS, log headers/body, or modify global proxy settings. The current module also preserves TCP half-close semantics.

1. WebKit 26.5 received HTTP 200 and the 1,607-byte public manifest through the relay. The saved first screenshot was opened with `view_image` and shows the actual JSON response.
2. A second raw CONNECT to the allowed public host remained idle as an established tunnel. Calling `stop()` closed the listener and both active tunnels, then joined all workers. Its returned snapshot has zero listener, socket and worker counts.
3. The established client socket received EOF. A new local connection was refused. A fresh uncached browser request failed with an explicit proxy connection-refused error. Upstream connection and byte counters remained equal to their values when `stop()` returned.
4. The second saved screenshot was opened with `view_image`; it shows the previous manifest document still visible after the failed navigation. It is not evidence of a successful new navigation.

The formal production WebKit flow may warm its real service worker cache while this relay is active, wait for `stop()` to return successfully, and then test a cache-served reload with the proxy transport unreachable. That application flow has not been run by this control. The previous WebKit `context.set_offline(True)` failures remain separate and are not reclassified.

The first relay version passed the narrower HTTPS/stop control in `../07a254e0-a019-4112-b897-f707ce245725/`. Review then found untested premature closure after one-direction EOF. The current version was repaired before application use. `../halfclose-c982215a-301b-4ac9-ba79-75297b4ff937/` retains a pure local socketpair RED/GREEN control: the old version delivered 0 bytes after a half-closed request; the repaired version delivered the full 1 MiB with the expected SHA-256. The current module was then independently re-run through this HTTPS/stop control.

Use the `SessionProxyForwarder` class from the saved `proxy_forwarder.py`. `start()` returns its local proxy URL; use it as the browser proxy server with the usual localhost bypass. Treat successful return of `stop()` as the transport-disconnection boundary. An early stop event alone is not that boundary. `stop()` raises if a listener, socket or worker remains alive.
