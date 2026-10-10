// Reference public OAuth client. PKCE, state, resource binding and token files
// are deliberately visible; it never needs an OAuth client secret.
package main

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/base64"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/go-training/mcp-oauth2-workshop/go/internal/workshop"
)

const protocolVersion = "2026-07-28"

var client = &http.Client{Timeout: 10 * time.Second, CheckRedirect: func(_ *http.Request, _ []*http.Request) error { return http.ErrUseLastResponse }}

type storedToken struct {
	AccessToken string `json:"access_token"`
	Issuer      string `json:"issuer"`
	Resource    string `json:"resource"`
}

func random() string {
	b := make([]byte, 48)
	if _, e := rand.Read(b); e != nil {
		panic(e)
	}
	return base64.RawURLEncoding.EncodeToString(b)
}
func load(path string) (storedToken, error) {
	var t storedToken
	b, e := os.ReadFile(path)
	if e != nil {
		return t, e
	}
	e = json.Unmarshal(b, &t)
	return t, e
}
func postForm(endpoint string, form url.Values) (map[string]any, error) {
	resp, e := client.PostForm(endpoint, form)
	if e != nil {
		return nil, e
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("upstream HTTP %d", resp.StatusCode)
	}
	var m map[string]any
	e = json.NewDecoder(io.LimitReader(resp.Body, 1<<20)).Decode(&m)
	return m, e
}
func login(issuer, resource, id, scope, path string, port int) error {
	if e := workshop.ValidateResource(resource); e != nil {
		return e
	}
	if id == "" {
		return errors.New("set OAUTH_CLIENT_ID to a pre-registered public client ID")
	}
	if _, e := os.Stat(path); e == nil {
		return errors.New("token file exists; select a new -token-file")
	}
	m, e := workshop.Discover(issuer)
	if e != nil {
		return e
	}
	methods, _ := m["code_challenge_methods_supported"].([]any)
	supported := false
	for _, v := range methods {
		if v == "S256" {
			supported = true
		}
	}
	if !supported {
		return errors.New("issuer does not advertise PKCE S256")
	}
	verifier, state := random(), random()
	sum := sha256.Sum256([]byte(verifier))
	challenge := base64.RawURLEncoding.EncodeToString(sum[:])
	ln, e := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", port))
	if e != nil {
		return e
	}
	redirect := "http://" + ln.Addr().String() + "/callback"
	received := make(chan url.Values, 1)
	srv := &http.Server{ReadHeaderTimeout: 5 * time.Second, Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		q := r.URL.Query()
		if r.URL.Path != "/callback" || subtle.ConstantTimeCompare([]byte(q.Get("state")), []byte(state)) != 1 {
			http.Error(w, "Invalid callback state", 400)
			return
		}
		select {
		case received <- q:
		default:
		}
		fmt.Fprint(w, "Callback received. Return to the terminal.")
	})}
	go srv.Serve(ln)
	defer srv.Close()
	authorize, ok := m["authorization_endpoint"].(string)
	if !ok {
		return errors.New("missing authorization_endpoint")
	}
	params := url.Values{"response_type": {"code"}, "client_id": {id}, "redirect_uri": {redirect}, "scope": {scope}, "state": {state}, "code_challenge": {challenge}, "code_challenge_method": {"S256"}, "resource": {resource}}
	fmt.Println("Open this URL in your browser:\n" + authorize + "?" + params.Encode())
	var callback url.Values
	select {
	case callback = <-received:
	case <-time.After(180 * time.Second):
		return errors.New("login timed out")
	}
	if callback.Get("error") != "" || callback.Get("code") == "" {
		return errors.New("authorization denied")
	}
	// RFC 9207: compare iss exactly; reject a missing iss when the server advertises it.
	if supported, _ := m["authorization_response_iss_parameter_supported"].(bool); supported && !callback.Has("iss") {
		return errors.New("callback missing issuer")
	}
	if callback.Has("iss") && callback.Get("iss") != issuer {
		return errors.New("callback issuer mismatch")
	}
	endpoint, ok := m["token_endpoint"].(string)
	if !ok {
		return errors.New("missing token_endpoint")
	}
	token, e := postForm(endpoint, url.Values{"grant_type": {"authorization_code"}, "client_id": {id}, "code": {callback.Get("code")}, "redirect_uri": {redirect}, "code_verifier": {verifier}, "resource": {resource}})
	if e != nil {
		return e
	}
	access, _ := token["access_token"].(string)
	typ, _ := token["token_type"].(string)
	if access == "" || !strings.EqualFold(typ, "bearer") {
		return errors.New("invalid token response")
	}
	if e = os.MkdirAll(filepath.Dir(path), 0700); e != nil {
		return e
	}
	f, e := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if e != nil {
		return e
	}
	defer f.Close()
	e = json.NewEncoder(f).Encode(storedToken{access, issuer, resource})
	if e == nil {
		fmt.Println("Saved access token with mode 0600; token value is not printed.")
	}
	return e
}
func rpc(resource, raw string, payload any, headers http.Header) (*http.Response, error) {
	b, e := json.Marshal(payload)
	if e != nil {
		return nil, e
	}
	req, e := http.NewRequestWithContext(context.Background(), "POST", resource, bytes.NewReader(b))
	if e != nil {
		return nil, e
	}
	req.Header = headers.Clone()
	req.Header.Set("Content-Type", "application/json")
	if raw != "" {
		req.Header.Set("Authorization", "Bearer "+raw)
	}
	return client.Do(req)
}
func call(resource, path, tool, text string, cross bool) error {
	if e := workshop.ValidateResource(resource); e != nil {
		return e
	}
	u, _ := url.Parse(resource)
	if cross && u.Hostname() != "localhost" && u.Hostname() != "127.0.0.1" {
		return errors.New("negative audience exercise is limited to local workshop servers")
	}
	t, e := load(path)
	if e != nil && !os.IsNotExist(e) {
		return e
	}
	if t.AccessToken != "" && t.Resource != resource && !cross {
		return errors.New("different resource; use -allow-cross-resource only for Lab 04")
	}
	// MCP 2026-07-28: no initialize handshake; every request carries its version in headers and _meta.
	h := http.Header{"Accept": {"application/json, text/event-stream"}, "Mcp-Protocol-Version": {protocolVersion}, "Mcp-Method": {"tools/call"}, "Mcp-Name": {tool}}
	args := map[string]any{}
	if tool == "create_note" {
		args["text"] = text
	}
	resp, e := rpc(resource, t.AccessToken, map[string]any{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": map[string]any{"name": tool, "arguments": args, "_meta": map[string]any{
		"io.modelcontextprotocol/protocolVersion":    protocolVersion,
		"io.modelcontextprotocol/clientInfo":         map[string]string{"name": "workshop-go-probe", "version": "1.0.0"},
		"io.modelcontextprotocol/clientCapabilities": map[string]any{},
	}}}, h)
	if e != nil {
		return e
	}
	defer resp.Body.Close()
	b, e := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if e != nil {
		return e
	}
	fmt.Println(resp.StatusCode, resp.Header.Get("WWW-Authenticate"), string(b))
	if resp.StatusCode != 200 {
		return errors.New("tool call denied")
	}
	var result struct {
		Error  any `json:"error"`
		Result struct {
			IsError bool `json:"isError"`
		} `json:"result"`
	}
	if e = json.Unmarshal(b, &result); e != nil {
		return e
	}
	if result.Error != nil || result.Result.IsError {
		return errors.New("MCP tool error")
	}
	return nil
}
func main() {
	command := flag.String("command", "call", "login, call, revoke, metadata")
	issuer := flag.String("issuer", os.Getenv("SIGNET_ISSUER"), "trusted Signet issuer")
	resourceDefault := os.Getenv("MCP_RESOURCE")
	if resourceDefault == "" {
		resourceDefault = "http://localhost:8000/mcp"
	}
	resource := flag.String("resource", resourceDefault, "canonical MCP resource URL")
	id := flag.String("client-id", os.Getenv("OAUTH_CLIENT_ID"), "pre-registered public client ID")
	scopes := flag.String("scopes", "notes:read", "space-separated scopes")
	path := flag.String("token-file", ".tokens/access.json", "private token file")
	port := flag.Int("callback-port", 8765, "loopback callback port")
	tool := flag.String("tool", "whoami", "MCP tool name")
	text := flag.String("text", "Hello workshop", "note text")
	cross := flag.Bool("allow-cross-resource", false, "only for Lab 04 negative audience test")
	flag.Parse()
	var e error
	switch *command {
	case "login":
		e = login(*issuer, *resource, *id, *scopes, *path, *port)
	case "call":
		e = call(*resource, *path, *tool, *text, *cross)
	case "metadata":
		var m map[string]any
		m, e = workshop.Discover(*issuer)
		if e == nil {
			e = json.NewEncoder(os.Stdout).Encode(m)
		}
	case "revoke":
		var t storedToken
		t, e = load(*path)
		if e == nil && t.Issuer != *issuer {
			e = errors.New("token issuer differs from configured issuer")
		}
		if e == nil {
			var m map[string]any
			m, e = workshop.Discover(*issuer)
			if e == nil {
				endpoint, ok := m["revocation_endpoint"].(string)
				if !ok {
					e = errors.New("missing revocation_endpoint")
				} else {
					var resp *http.Response
					resp, e = client.PostForm(endpoint, url.Values{"token": {t.AccessToken}, "token_type_hint": {"access_token"}})
					if e == nil {
						resp.Body.Close()
						if resp.StatusCode != 200 {
							e = fmt.Errorf("revocation HTTP %d", resp.StatusCode)
						} else {
							fmt.Println("Revocation accepted. Keep file to test SAME token again.")
						}
					}
				}
			}
		}
	default:
		e = errors.New("unknown command")
	}
	if e != nil {
		fmt.Fprintln(os.Stderr, "Error:", e)
		os.Exit(1)
	}
}
