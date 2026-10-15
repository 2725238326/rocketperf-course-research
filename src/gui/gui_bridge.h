#ifndef ROCKETPERF_GUI_BRIDGE_H
#define ROCKETPERF_GUI_BRIDGE_H

/* One GUI request (flat JSON, see gui_json.h) -> malloc'ed JSON envelope:
 *   {"ok":true,"cmd":"..","elapsed_ms":..,"result":{..}}
 *   {"ok":false,"cmd":"..","status":"out_of_domain","stage":"..","message":".."}
 * The bridge only maps arguments to the existing C solvers and serializes their
 * outputs; physical domains and failures come from the core unchanged.
 * Thread-safe: solvers keep no global mutable state and each call owns its
 * buffers. Returns NULL only when memory for the envelope cannot be allocated. */
char *rp_gui_handle(const char *request);
void rp_gui_release(char *response);

#endif
