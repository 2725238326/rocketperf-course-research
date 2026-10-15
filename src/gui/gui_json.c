#include "gui_json.h"
#include "rocketperf/numeric.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    const char *at;
    const char *reason;
} Cursor;

static void skip(Cursor *c)
{
    while (*c->at == ' ' || *c->at == '\t' || *c->at == '\n' || *c->at == '\r') { ++c->at; }
}

static int expect(Cursor *c, char token)
{
    skip(c);
    if (*c->at != token) { return 0; }
    ++c->at;
    return 1;
}

static int fail(Cursor *c, const char *reason)
{
    if (c->reason == NULL) { c->reason = reason; }
    return 0;
}

static int hex_digit(char ch)
{
    if (ch >= '0' && ch <= '9') { return ch - '0'; }
    if (ch >= 'a' && ch <= 'f') { return ch - 'a' + 10; }
    if (ch >= 'A' && ch <= 'F') { return ch - 'A' + 10; }
    return -1;
}

/* Decodes a JSON string into UTF-8; BMP \u escapes only, surrogates rejected. */
static int parse_string(Cursor *c, char *output, size_t capacity)
{
    size_t length = 0U;
    skip(c);
    if (*c->at != '"') { return fail(c, "expected string"); }
    ++c->at;
    while (*c->at != '"') {
        unsigned char ch = (unsigned char)*c->at;
        char encoded[3];
        size_t width = 1U;
        if (ch == 0U || ch < 0x20U) { return fail(c, "control character in string"); }
        if (ch == '\\') {
            ++c->at;
            switch (*c->at) {
            case '"': encoded[0] = '"'; break;
            case '\\': encoded[0] = '\\'; break;
            case '/': encoded[0] = '/'; break;
            case 'n': encoded[0] = '\n'; break;
            case 't': encoded[0] = '\t'; break;
            case 'r': encoded[0] = '\r'; break;
            case 'b': encoded[0] = '\b'; break;
            case 'f': encoded[0] = '\f'; break;
            case 'u': {
                unsigned int code = 0U;
                for (int i = 1; i <= 4; ++i) {
                    const int digit = hex_digit(c->at[i]);
                    if (digit < 0) { return fail(c, "bad unicode escape"); }
                    code = code * 16U + (unsigned int)digit;
                }
                c->at += 4;
                if (code == 0U || (code >= 0xD800U && code <= 0xDFFFU)) { return fail(c, "unsupported unicode escape"); }
                if (code < 0x80U) { encoded[0] = (char)code; }
                else if (code < 0x800U) {
                    encoded[0] = (char)(0xC0U | (code >> 6)); encoded[1] = (char)(0x80U | (code & 0x3FU)); width = 2U;
                } else {
                    encoded[0] = (char)(0xE0U | (code >> 12)); encoded[1] = (char)(0x80U | ((code >> 6) & 0x3FU));
                    encoded[2] = (char)(0x80U | (code & 0x3FU)); width = 3U;
                }
                break;
            }
            default: return fail(c, "unknown escape");
            }
        } else {
            encoded[0] = (char)ch;
        }
        if (length + width >= capacity) { return fail(c, "string too long"); }
        memcpy(output + length, encoded, width);
        length += width;
        ++c->at;
    }
    ++c->at;
    output[length] = '\0';
    return 1;
}

/* JSON number grammar start; strtod then rejects hex/inf/nan forms. */
static int parse_number(Cursor *c, double *output)
{
    char *end;
    double value;
    skip(c);
    if (!(*c->at == '-' || (*c->at >= '0' && *c->at <= '9'))) { return fail(c, "expected number"); }
    value = strtod(c->at, &end);
    for (const char *p = c->at; p < end; ++p) {
        if (*p == 'x' || *p == 'X' || *p == 'n' || *p == 'N' || *p == 'i' || *p == 'I') { return fail(c, "invalid number"); }
    }
    if (end == c->at || !rp_isfinite(value)) { return fail(c, "invalid number"); }
    c->at = end;
    *output = value;
    return 1;
}

static int literal(Cursor *c, const char *word)
{
    const size_t length = strlen(word);
    if (strncmp(c->at, word, length) != 0) { return 0; }
    c->at += length;
    return 1;
}

static int parse_value(Cursor *c, RpGuiField *field)
{
    skip(c);
    if (*c->at == '"') { field->kind = RP_GUI_TEXT; return parse_string(c, field->text, sizeof(field->text)); }
    if (literal(c, "true")) { field->kind = RP_GUI_BOOL; field->boolean = 1; return 1; }
    if (literal(c, "false")) { field->kind = RP_GUI_BOOL; field->boolean = 0; return 1; }
    if (*c->at == '[') {
        ++c->at;
        field->kind = RP_GUI_ARRAY;
        field->count = 0U;
        skip(c);
        if (*c->at == ']') { ++c->at; return 1; }
        for (;;) {
            if (field->count >= RP_GUI_ARRAY_MAX) { return fail(c, "array too long"); }
            if (!parse_number(c, &field->array[field->count])) { return 0; }
            ++field->count;
            skip(c);
            if (*c->at == ',') { ++c->at; continue; }
            if (*c->at == ']') { ++c->at; return 1; }
            return fail(c, "expected , or ] in array");
        }
    }
    field->kind = RP_GUI_NUMBER;
    return parse_number(c, &field->number);
}

static int parse_args(Cursor *c, RpGuiRequest *request)
{
    if (!expect(c, '{')) { return fail(c, "args must be an object"); }
    skip(c);
    if (*c->at == '}') { ++c->at; return 1; }
    for (;;) {
        RpGuiField *field;
        if (request->count >= RP_GUI_FIELD_MAX) { return fail(c, "too many arguments"); }
        field = &request->fields[request->count];
        memset(field, 0, sizeof(*field));
        if (!parse_string(c, field->key, sizeof(field->key))) { return 0; }
        if (rp_gui_field(request, field->key) != NULL) { return fail(c, "duplicate argument"); }
        if (!expect(c, ':')) { return fail(c, "expected :"); }
        if (!parse_value(c, field)) { return 0; }
        ++request->count;
        skip(c);
        if (*c->at == ',') { ++c->at; continue; }
        if (*c->at == '}') { ++c->at; return 1; }
        return fail(c, "expected , or } in args");
    }
}

int rp_gui_parse(const char *text, RpGuiRequest *output, char *reason, size_t capacity)
{
    Cursor c = {text, NULL};
    int wrapped = 0;
    int seen_cmd = 0;
    int ok = 1;
    if (text == NULL || output == NULL) { return 0; }
    memset(output, 0, sizeof(*output));
    skip(&c);
    if (*c.at == '[') { ++c.at; wrapped = 1; }
    if (!expect(&c, '{')) { ok = fail(&c, "request must be an object"); }
    while (ok) {
        char key[RP_GUI_KEY_MAX];
        skip(&c);
        if (*c.at == '}') { ++c.at; break; }
        if (!parse_string(&c, key, sizeof(key)) || !expect(&c, ':')) { ok = fail(&c, "bad request key"); break; }
        if (strcmp(key, "cmd") == 0 && !seen_cmd) {
            ok = parse_string(&c, output->cmd, sizeof(output->cmd));
            seen_cmd = 1;
        } else if (strcmp(key, "args") == 0) {
            ok = parse_args(&c, output);
        } else {
            ok = fail(&c, "unknown request key");
        }
        if (!ok) { break; }
        skip(&c);
        if (*c.at == ',') { ++c.at; continue; }
        if (*c.at == '}') { ++c.at; break; }
        ok = fail(&c, "expected , or } in request");
    }
    if (ok && wrapped && !expect(&c, ']')) { ok = fail(&c, "expected ]"); }
    if (ok) { skip(&c); if (*c.at != '\0') { ok = fail(&c, "trailing characters"); } }
    if (ok && !seen_cmd) { ok = fail(&c, "missing cmd"); }
    if (!ok && reason != NULL && capacity > 0U) {
        (void)snprintf(reason, capacity, "%s", c.reason != NULL ? c.reason : "malformed request");
    }
    return ok;
}

const RpGuiField *rp_gui_field(const RpGuiRequest *request, const char *key)
{
    for (size_t i = 0U; i < request->count; ++i) {
        if (strcmp(request->fields[i].key, key) == 0) { return &request->fields[i]; }
    }
    return NULL;
}

void rp_gui_buffer_free(RpGuiBuffer *buffer)
{
    free(buffer->data);
    buffer->data = NULL;
    buffer->length = buffer->capacity = 0U;
}

static void append(RpGuiBuffer *buffer, const char *text, size_t length)
{
    if (buffer->failed) { return; }
    if (buffer->length + length + 1U > buffer->capacity) {
        size_t capacity = buffer->capacity == 0U ? 4096U : buffer->capacity;
        char *grown;
        while (buffer->length + length + 1U > capacity) { capacity *= 2U; }
        grown = realloc(buffer->data, capacity);
        if (grown == NULL) { buffer->failed = 1; return; }
        buffer->data = grown;
        buffer->capacity = capacity;
    }
    memcpy(buffer->data + buffer->length, text, length);
    buffer->length += length;
    buffer->data[buffer->length] = '\0';
}

void rp_gui_raw(RpGuiBuffer *buffer, const char *text) { append(buffer, text, strlen(text)); }

void rp_gui_open(RpGuiBuffer *buffer, char bracket)
{
    const char text[2] = {bracket, '\0'};
    append(buffer, text, 1U);
}

void rp_gui_close(RpGuiBuffer *buffer, char bracket)
{
    const char text[3] = {bracket, ',', '\0'};
    if (!buffer->failed && buffer->length > 0U && buffer->data[buffer->length - 1U] == ',') {
        buffer->data[buffer->length - 1U] = bracket;
        append(buffer, ",", 1U);
        return;
    }
    append(buffer, text, 2U);
}

void rp_gui_string(RpGuiBuffer *buffer, const char *text)
{
    append(buffer, "\"", 1U);
    for (const unsigned char *p = (const unsigned char *)text; *p != 0U; ++p) {
        char escaped[8];
        if (*p == '"' || *p == '\\') { escaped[0] = '\\'; escaped[1] = (char)*p; append(buffer, escaped, 2U); }
        else if (*p < 0x20U) { (void)snprintf(escaped, sizeof(escaped), "\\u%04x", (unsigned int)*p); append(buffer, escaped, 6U); }
        else { append(buffer, (const char *)p, 1U); }
    }
    append(buffer, "\"", 1U);
}

void rp_gui_key(RpGuiBuffer *buffer, const char *key)
{
    rp_gui_string(buffer, key);
    append(buffer, ":", 1U);
}

void rp_gui_number(RpGuiBuffer *buffer, double value)
{
    char text[40];
    int written;
    if (!rp_isfinite(value)) { append(buffer, "null,", 5U); return; }
    written = snprintf(text, sizeof(text), "%.10g,", value);
    if (written <= 0 || (size_t)written >= sizeof(text)) { buffer->failed = 1; return; }
    append(buffer, text, (size_t)written);
}

void rp_gui_num(RpGuiBuffer *buffer, const char *key, double value)
{
    rp_gui_key(buffer, key);
    rp_gui_number(buffer, value);
}

void rp_gui_text(RpGuiBuffer *buffer, const char *key, const char *text)
{
    rp_gui_key(buffer, key);
    rp_gui_string(buffer, text);
    append(buffer, ",", 1U);
}

void rp_gui_flag(RpGuiBuffer *buffer, const char *key, int value)
{
    rp_gui_key(buffer, key);
    rp_gui_raw(buffer, value ? "true," : "false,");
}

void rp_gui_numbers(RpGuiBuffer *buffer, const char *key, const double *values, size_t count)
{
    if (key != NULL) { rp_gui_key(buffer, key); }
    rp_gui_open(buffer, '[');
    for (size_t i = 0U; i < count; ++i) { rp_gui_number(buffer, values[i]); }
    rp_gui_close(buffer, ']');
}
