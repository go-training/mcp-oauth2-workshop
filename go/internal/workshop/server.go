// Package workshop contains the transport and authorization layers shared by the labs.
// Read NewHandler and authorize in order: discovery -> JWT -> scope -> revocation.
package workshop

import (
	"bytes"
	"context"
	"crypto/subtle"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/MicahParks/keyfunc/v3"
	"github.com/golang-jwt/jwt/v5"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

type Config struct {
	Lab                                                 int
	Listen, Resource, Issuer, ReadScope, WriteScope     string
	IntrospectionID, IntrospectionSecret, GatewaySecret string
}

func env(key, fallback string) string {
	if s := os.Getenv(key); s != "" {
		return s
	}
	return fallback
}
func LoadConfig(lab int) Config {
	return Config{lab, env("LISTEN_ADDR", "127.0.0.1:8000"), env("MCP_RESOURCE", "http://localhost:8000/mcp"), os.Getenv("SIGNET_ISSUER"), env("READ_SCOPE", "notes:read"), env("WRITE_SCOPE", "notes:write"), os.Getenv("INTROSPECTION_CLIENT_ID"), os.Getenv("INTROSPECTION_CLIENT_SECRET"), os.Getenv("GATEWAY_SHARED_SECRET")}
}

// TrustedURL allows plaintext only for explicitly enabled loopback test fixtures.
func TrustedURL(raw string) error {
	u, e := url.Parse(raw)
	if e != nil || u.Host == "" || u.User != nil || u.Fragment != "" {
		return fmt.Errorf("invalid trusted URL")
	}
	if u.Scheme == "https" {
		return nil
	}
	if os.Getenv("ALLOW_INSECURE_ISSUER") == "1" && u.Scheme == "http" && (u.Hostname() == "127.0.0.1" || u.Hostname() == "localhost" || u.Hostname() == "::1") {
		return nil
	}
	return errors.New("issuer and its endpoints must use HTTPS")
}

var httpClient = &http.Client{Timeout: 5 * time.Second, CheckRedirect: func(_ *http.Request, _ []*http.Request) error { return http.ErrUseLastResponse }}

func readJSON(resp *http.Response, out any) error {
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return fmt.Errorf("upstream HTTP %d", resp.StatusCode)
	}
	return json.NewDecoder(io.LimitReader(resp.Body, 1<<20)).Decode(out)
}

// Discover follows the 2025-11-25 issuer-path discovery order, validating issuer equality.
func Discover(issuer string) (map[string]any, error) {
	if e := TrustedURL(issuer); e != nil {
		return nil, e
	}
	u, _ := url.Parse(issuer)
	origin := u.Scheme + "://" + u.Host
	path := strings.TrimRight(u.Path, "/")
	candidates := []string{origin + "/.well-known/oauth-authorization-server" + path, origin + "/.well-known/openid-configuration" + path}
	if path != "" {
		candidates = append(candidates, origin+path+"/.well-known/openid-configuration")
	}
	for _, endpoint := range candidates {
		resp, e := httpClient.Get(endpoint)
		if e != nil {
			continue
		}
		var m map[string]any
		if e = readJSON(resp, &m); e != nil {
			continue
		}
		if m["issuer"] != issuer {
			return nil, errors.New("metadata issuer mismatch")
		}
		for _, k := range []string{"jwks_uri", "authorization_endpoint", "token_endpoint", "revocation_endpoint", "introspection_endpoint"} {
			if v, ok := m[k].(string); ok {
				if e = TrustedURL(v); e != nil {
					return nil, fmt.Errorf("%s: %w", k, e)
				}
			}
		}
		return m, nil
	}
	return nil, errors.New("authorization server discovery failed")
}

type identity struct {
	Subject  string `json:"subject"`
	Scope    string `json:"scope"`
	Audience any    `json:"audience"`
	TokenID  string `json:"token_id,omitempty"`
}
type identityKey struct{}

func user(ctx context.Context) identity { v, _ := ctx.Value(identityKey{}).(identity); return v }

type app struct {
	cfg         Config
	metadataURL string
	keys        keyfunc.Keyfunc
	introspect  string
	mu          sync.Mutex
	notes       map[string][]string
}

// ValidateResource prevents sending bearer credentials over non-loopback plaintext HTTP.
func ValidateResource(raw string) error {
	u, e := url.Parse(raw)
	if e != nil || u.Host == "" || u.Path != "/mcp" || u.RawQuery != "" || u.Fragment != "" || u.User != nil {
		return errors.New("invalid MCP resource URL")
	}
	if u.Scheme == "https" || (u.Scheme == "http" && (u.Hostname() == "localhost" || u.Hostname() == "127.0.0.1")) {
		return nil
	}
	return errors.New("resource must use HTTPS or loopback HTTP")
}

func NewHandler(ctx context.Context, c Config) (http.Handler, error) {
	if c.Lab < 1 || c.Lab > 6 {
		return nil, errors.New("lab must be 1..6")
	}
	u, e := url.Parse(c.Resource)
	if e != nil || u.Host == "" || u.Path != "/mcp" || u.RawQuery != "" || u.Fragment != "" || u.User != nil {
		return nil, errors.New("MCP_RESOURCE must be an absolute URL ending exactly in /mcp")
	}
	if u.Scheme != "https" && !(u.Scheme == "http" && (u.Hostname() == "localhost" || u.Hostname() == "127.0.0.1")) {
		return nil, errors.New("plaintext resource is allowed only on loopback")
	}
	a := &app{cfg: c, metadataURL: u.Scheme + "://" + u.Host + "/.well-known/oauth-protected-resource/mcp", notes: map[string][]string{}}
	if c.Lab >= 2 && c.Lab <= 5 {
		if e = TrustedURL(c.Issuer); e != nil {
			return nil, e
		}
	}
	if c.Lab >= 3 && c.Lab <= 5 {
		m, e := Discover(c.Issuer)
		if e != nil {
			return nil, e
		}
		jwks, _ := m["jwks_uri"].(string)
		if jwks == "" {
			return nil, errors.New("metadata missing jwks_uri")
		}
		a.keys, e = keyfunc.NewDefaultCtx(ctx, []string{jwks})
		if e != nil {
			return nil, e
		}
		if c.Lab == 5 {
			a.introspect, _ = m["introspection_endpoint"].(string)
			if a.introspect == "" || c.IntrospectionID == "" || c.IntrospectionSecret == "" {
				return nil, errors.New("Lab 05 requires introspection endpoint and per-team confidential client credentials")
			}
		}
	}
	if c.Lab == 6 && len(c.GatewaySecret) < 32 {
		return nil, errors.New("Lab 06 requires a random GATEWAY_SHARED_SECRET of at least 32 characters")
	}
	s := mcp.NewServer(&mcp.Implementation{Name: fmt.Sprintf("workshop-go-lab%02d", c.Lab), Version: "1.0.0"}, nil)
	mcp.AddTool(s, &mcp.Tool{Name: "whoami", Description: "Show the verified workshop identity; never returns a raw token"}, func(ctx context.Context, _ *mcp.CallToolRequest, _ struct{}) (*mcp.CallToolResult, identity, error) {
		return nil, user(ctx), nil
	})
	type noteList struct {
		Notes []string `json:"notes"`
	}
	mcp.AddTool(s, &mcp.Tool{Name: "list_notes", Description: "Read your own in-memory workshop notes"}, func(ctx context.Context, _ *mcp.CallToolRequest, _ struct{}) (*mcp.CallToolResult, noteList, error) {
		a.mu.Lock()
		defer a.mu.Unlock()
		return nil, noteList{append([]string{}, a.notes[user(ctx).Subject]...)}, nil
	})
	type noteInput struct {
		Text string `json:"text" jsonschema:"A synthetic workshop note, at most 500 characters"`
	}
	mcp.AddTool(s, &mcp.Tool{Name: "create_note", Description: "Create a note; requires notes:write in Lab 04 and later"}, func(ctx context.Context, _ *mcp.CallToolRequest, in noteInput) (*mcp.CallToolResult, noteList, error) {
		id := user(ctx)
		if c.Lab >= 4 && !hasScope(id.Scope, c.WriteScope) {
			return nil, noteList{}, errors.New("insufficient_scope")
		}
		if len([]rune(in.Text)) < 1 || len([]rune(in.Text)) > 500 {
			return nil, noteList{}, errors.New("text must have 1..500 characters")
		}
		a.mu.Lock()
		defer a.mu.Unlock()
		if len(a.notes[id.Subject]) >= 100 {
			return nil, noteList{}, errors.New("workshop note limit reached")
		}
		a.notes[id.Subject] = append(a.notes[id.Subject], in.Text)
		return nil, noteList{append([]string{}, a.notes[id.Subject]...)}, nil
	})
	h := mcp.NewStreamableHTTPHandler(func(*http.Request) *mcp.Server { return s }, &mcp.StreamableHTTPOptions{Stateless: true, JSONResponse: true})
	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) { w.Write([]byte("ok")) })
	if c.Lab >= 2 && c.Lab <= 5 {
		for _, path := range []string{"/.well-known/oauth-protected-resource/mcp", "/.well-known/oauth-protected-resource"} {
			mux.HandleFunc(path, func(w http.ResponseWriter, r *http.Request) {
				if r.Method != "GET" {
					w.WriteHeader(405)
					return
				}
				writeJSON(w, 200, map[string]any{"resource": c.Resource, "authorization_servers": []string{c.Issuer}, "scopes_supported": []string{c.ReadScope}, "bearer_methods_supported": []string{"header"}})
			})
		}
	}
	mux.Handle("/mcp", a.authorize(h))
	// Native CLI clients do not send Origin. Browser origins must exactly match the resource origin.
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if o := r.Header.Get("Origin"); o != "" && o != u.Scheme+"://"+u.Host {
			writeJSON(w, 403, map[string]string{"error": "untrusted_origin"})
			return
		}
		mux.ServeHTTP(w, r)
	}), nil
}
func hasScope(raw, required string) bool {
	for _, s := range strings.Fields(raw) {
		if s == required {
			return true
		}
	}
	return false
}
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
func (a *app) reject(w http.ResponseWriter, status int, code, scope string) {
	if status == 401 || status == 403 {
		w.Header().Set("WWW-Authenticate", fmt.Sprintf("Bearer resource_metadata=%q, error=%q, scope=%q", a.metadataURL, code, scope))
	}
	slog.Info("authorization denied", "lab", a.cfg.Lab, "status", status, "reason", code)
	writeJSON(w, status, map[string]string{"error": code})
}
func (a *app) verify(raw string) (identity, error) {
	claims := jwt.MapClaims{}
	_, e := jwt.ParseWithClaims(raw, claims, a.keys.Keyfunc, jwt.WithValidMethods([]string{"RS256"}), jwt.WithIssuer(a.cfg.Issuer), jwt.WithAudience(a.cfg.Resource), jwt.WithExpirationRequired(), jwt.WithIssuedAt())
	if e != nil {
		return identity{}, e
	}
	sub, _ := claims["sub"].(string)
	scope, ok := claims["scope"].(string)
	jti, _ := claims["jti"].(string)
	if claims["type"] != "access" || sub == "" || !ok {
		return identity{}, errors.New("invalid access token claims")
	}
	return identity{sub, scope, claims["aud"], jti}, nil
}
func (a *app) active(ctx context.Context, raw string) (bool, error) {
	form := url.Values{"token": {raw}, "token_type_hint": {"access_token"}}
	req, e := http.NewRequestWithContext(ctx, "POST", a.introspect, strings.NewReader(form.Encode()))
	if e != nil {
		return false, e
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.SetBasicAuth(url.QueryEscape(a.cfg.IntrospectionID), url.QueryEscape(a.cfg.IntrospectionSecret))
	resp, e := httpClient.Do(req)
	if e != nil {
		return false, e
	}
	var result struct {
		Active *bool `json:"active"`
	}
	if e = readJSON(resp, &result); e != nil {
		return false, e
	}
	if result.Active == nil {
		return false, errors.New("invalid introspection response")
	}
	return *result.Active, nil
}
func (a *app) authorize(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		c := a.cfg
		id := identity{Subject: "anonymous", Scope: "", Audience: c.Resource}
		if r.URL.Query().Has("access_token") {
			a.reject(w, 400, "token_in_query_forbidden", c.ReadScope)
			return
		}
		if c.Lab == 2 {
			a.reject(w, 401, "invalid_token", c.ReadScope)
			return
		}
		if c.Lab >= 3 && c.Lab <= 5 {
			parts := strings.Fields(r.Header.Get("Authorization"))
			if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
				a.reject(w, 401, "invalid_token", c.ReadScope)
				return
			}
			var e error
			id, e = a.verify(parts[1])
			if e != nil {
				a.reject(w, 401, "invalid_token", c.ReadScope)
				return
			}
			if c.Lab == 5 {
				active, e := a.active(r.Context(), parts[1])
				if e != nil {
					a.reject(w, 503, "temporarily_unavailable", c.ReadScope)
					return
				}
				if !active {
					a.reject(w, 401, "invalid_token", c.ReadScope)
					return
				}
			}
		}
		if c.Lab == 6 {
			if subtle.ConstantTimeCompare([]byte(r.Header.Get("X-Workshop-Gateway")), []byte(c.GatewaySecret)) != 1 {
				a.reject(w, 401, "untrusted_gateway", c.ReadScope)
				return
			}
			id = identity{r.Header.Get("X-MCP-Subject"), r.Header.Get("X-MCP-Scope"), r.Header.Get("X-MCP-Audience"), r.Header.Get("X-MCP-Token-Id")}
			if id.Subject == "" || r.Header.Get("X-MCP-Issuer") != c.Issuer || id.Audience != c.Resource {
				a.reject(w, 401, "invalid_gateway_identity", c.ReadScope)
				return
			}
		}
		if c.Lab >= 3 && !hasScope(id.Scope, c.ReadScope) {
			a.reject(w, 403, "insufficient_scope", c.ReadScope)
			return
		}
		if c.Lab >= 4 && r.Method == "POST" {
			b, e := io.ReadAll(http.MaxBytesReader(w, r.Body, 1<<20))
			if e != nil {
				writeJSON(w, 413, map[string]string{"error": "request_too_large"})
				return
			}
			r.Body = io.NopCloser(bytes.NewReader(b))
			var rpc struct {
				Method string `json:"method"`
				Params struct {
					Name string `json:"name"`
				} `json:"params"`
			}
			if json.Unmarshal(b, &rpc) == nil && rpc.Method == "tools/call" && rpc.Params.Name == "create_note" && !hasScope(id.Scope, c.WriteScope) {
				a.reject(w, 403, "insufficient_scope", c.ReadScope+" "+c.WriteScope)
				return
			}
		}
		slog.Info("authorized request", "lab", c.Lab, "subject", id.Subject, "token_id", id.TokenID, "method", r.Method)
		next.ServeHTTP(w, r.WithContext(context.WithValue(r.Context(), identityKey{}, id)))
	})
}
func Run(lab int) {
	c := LoadConfig(lab)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	h, e := NewHandler(ctx, c)
	if e != nil {
		slog.Error("configuration failed", "error", e)
		os.Exit(1)
	}
	slog.Info("MCP ready", "lab", lab, "listen", c.Listen, "resource", c.Resource)
	srv := &http.Server{Addr: c.Listen, Handler: h, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 30 * time.Second, IdleTimeout: 60 * time.Second}
	if e = srv.ListenAndServe(); e != nil {
		slog.Error("server stopped", "error", e)
		os.Exit(1)
	}
}
