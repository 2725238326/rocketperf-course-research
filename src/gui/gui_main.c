/* Desktop window: WebView2 page + C bridge. Every calculation runs in
 * rp_gui_handle on a worker thread; the page only renders C results.
 * webview (MIT, third_party/webview) is the only non-system dependency and is
 * linked statically; the WebView2 runtime ships with Windows 10/11. */
#include "gui_bridge.h"

#include <webview/webview.h>

#include <process.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

#define RP_GUI_PAGE_ID 100
#define RP_GUI_STYLE_FIRST 101
#define RP_GUI_SCRIPT_FIRST 201
#define RP_GUI_ASSET_SPAN 99

static volatile LONG pending_jobs = 0;
static webview_t view = NULL;

typedef struct {
    char *id;
    char *request;
} Job;

static char *copy_text(const char *text)
{
    const size_t length = strlen(text) + 1U;
    char *copy = malloc(length);
    if (copy != NULL) { memcpy(copy, text, length); }
    return copy;
}

static unsigned __stdcall work(void *argument)
{
    Job *job = argument;
    char *response = rp_gui_handle(job->request);
    (void)webview_return(view, job->id, 0, response != NULL ? response :
        "{\"ok\":false,\"cmd\":\"\",\"elapsed_ms\":0,\"status\":\"io_error\",\"stage\":\"bridge\",\"message\":\"Cannot allocate response.\"}");
    rp_gui_release(response);
    free(job->id);
    free(job->request);
    free(job);
    (void)InterlockedDecrement(&pending_jobs);
    return 0U;
}

/* Bound as window.rp(request); returns immediately and replies from a worker. */
static void dispatch(const char *id, const char *request, void *argument)
{
    Job *job = malloc(sizeof(*job));
    uintptr_t thread;
    (void)argument;
    if (job == NULL || (job->id = copy_text(id)) == NULL || (job->request = copy_text(request)) == NULL) {
        if (job != NULL) { free(job->id); }
        free(job);
        (void)webview_return(view, id, 1, "\"out of memory\"");
        return;
    }
    (void)InterlockedIncrement(&pending_jobs);
    thread = _beginthreadex(NULL, 0U, work, job, 0U, NULL);
    if (thread == 0U) {
        (void)InterlockedDecrement(&pending_jobs);
        (void)webview_return(view, id, 1, "\"cannot start worker thread\"");
        free(job->id); free(job->request); free(job);
        return;
    }
    (void)CloseHandle((HANDLE)thread);
}

/* Borderless fullscreen toggle on the host window (WebView2 has no F11). */
static void fullscreen(const char *id, const char *request, void *argument)
{
    static WINDOWPLACEMENT placement = {sizeof(WINDOWPLACEMENT), 0U, 0U, {0, 0}, {0, 0}, {0, 0, 0, 0}};
    HWND window = (HWND)webview_get_window(view);
    const LONG_PTR style = GetWindowLongPtrW(window, GWL_STYLE);
    (void)request; (void)argument;
    if ((style & (LONG_PTR)WS_OVERLAPPEDWINDOW) != 0) {
        MONITORINFO monitor = {sizeof(MONITORINFO), {0, 0, 0, 0}, {0, 0, 0, 0}, 0U};
        if (GetWindowPlacement(window, &placement) &&
            GetMonitorInfoW(MonitorFromWindow(window, MONITOR_DEFAULTTOPRIMARY), &monitor)) {
            (void)SetWindowLongPtrW(window, GWL_STYLE, style & ~(LONG_PTR)WS_OVERLAPPEDWINDOW);
            (void)SetWindowPos(window, HWND_TOP, monitor.rcMonitor.left, monitor.rcMonitor.top,
                               monitor.rcMonitor.right - monitor.rcMonitor.left,
                               monitor.rcMonitor.bottom - monitor.rcMonitor.top, SWP_NOOWNERZORDER | SWP_FRAMECHANGED);
        }
    } else {
        (void)SetWindowLongPtrW(window, GWL_STYLE, style | (LONG_PTR)WS_OVERLAPPEDWINDOW);
        (void)SetWindowPlacement(window, &placement);
        (void)SetWindowPos(window, NULL, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOOWNERZORDER | SWP_FRAMECHANGED);
    }
    (void)webview_return(view, id, 0, "true");
}

typedef struct { char *data; size_t length; } Text;

static int resource(int id, const char **data, size_t *length)
{
    HRSRC found = FindResourceW(NULL, MAKEINTRESOURCEW(id), MAKEINTRESOURCEW(10));
    HGLOBAL loaded;
    if (found == NULL || (loaded = LoadResource(NULL, found)) == NULL) { return 0; }
    *data = LockResource(loaded);
    *length = SizeofResource(NULL, found);
    return *data != NULL;
}

static int append(Text *text, const char *data, size_t length)
{
    char *grown = realloc(text->data, text->length + length + 1U);
    if (grown == NULL) { return 0; }
    memcpy(grown + text->length, data, length);
    text->data = grown;
    text->length += length;
    text->data[text->length] = '\0';
    return 1;
}

/* Page shell with stylesheets and scripts (contiguous RCDATA IDs) spliced in. */
static int append_group(Text *text, int first)
{
    for (int id = first; id < first + RP_GUI_ASSET_SPAN; ++id) {
        const char *data;
        size_t length;
        if (!resource(id, &data, &length)) { return 1; }
        if (!append(text, data, length) || !append(text, "\n", 1U)) { return 0; }
    }
    return 1;
}

static char *assemble_page(void)
{
    const char *page, *style, *script;
    size_t length;
    Text text = {NULL, 0U};
    if (!resource(RP_GUI_PAGE_ID, &page, &length)) { return NULL; }
    {
        const char *end = page + length;
        style = strstr(page, "/*STYLE*/");
        script = strstr(page, "/*SCRIPT*/");
        if (style == NULL || script == NULL || style > script || script >= end) { return NULL; }
        if (!append(&text, page, (size_t)(style - page)) || !append_group(&text, RP_GUI_STYLE_FIRST) ||
            !append(&text, style + 9, (size_t)(script - style - 9)) || !append_group(&text, RP_GUI_SCRIPT_FIRST) ||
            !append(&text, script + 10, (size_t)(end - script - 10))) {
            free(text.data);
            return NULL;
        }
    }
    return text.data;
}

int WINAPI WinMain(HINSTANCE instance, HINSTANCE previous, LPSTR command_line, int show)
{
    char *page;
    const int debug = command_line != NULL && strstr(command_line, "--debug") != NULL;
    (void)instance; (void)previous; (void)show;
    page = assemble_page();
    if (page == NULL) {
        (void)MessageBoxW(NULL, L"界面资源缺失或损坏。", L"RocketPerf", MB_ICONERROR);
        return 3;
    }
    view = webview_create(debug, NULL);
    if (view == NULL) {
        (void)MessageBoxW(NULL, L"无法启动 WebView2。请安装 Microsoft Edge WebView2 Runtime，或使用控制台版 rocketperf.exe。",
                          L"RocketPerf", MB_ICONERROR);
        free(page);
        return 3;
    }
    (void)webview_set_title(view, "RocketPerf 液体火箭发动机性能计算");
    (void)webview_set_size(view, 1480, 920, WEBVIEW_HINT_NONE);
    (void)webview_set_size(view, 1100, 700, WEBVIEW_HINT_MIN);
    (void)webview_bind(view, "rp", dispatch, NULL);
    (void)webview_bind(view, "rp_fullscreen", fullscreen, NULL);
    (void)webview_set_html(view, page);
    free(page);
    (void)webview_run(view);
    while (InterlockedCompareExchange(&pending_jobs, 0, 0) > 0) { Sleep(5); }
    (void)webview_destroy(view);
    return 0;
}
