package workshop

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestValidateResource(t *testing.T) {
	for _, tc := range []struct {
		url   string
		valid bool
	}{
		{"https://example.com/mcp", true},
		{"http://localhost:8000/mcp", true},
		{"http://127.0.0.1:8000/mcp", true},
		{"http://remote.example/mcp", false},
		{"https://example.com/other", false},
		{"https://example.com/mcp?access_token=secret", false},
		{"https://example.com/mcp#fragment", false},
		{"https://user:password@example.com/mcp", false},
		{"/mcp", false},
	} {
		t.Run(tc.url, func(t *testing.T) {
			if err := ValidateResource(tc.url); (err == nil) != tc.valid {
				t.Fatalf("ValidateResource(%q) = %v, want valid=%v", tc.url, err, tc.valid)
			}
		})
	}
}

func TestTrustedURL(t *testing.T) {
	for _, allow := range []string{"", "1"} {
		t.Run("allow_insecure="+allow, func(t *testing.T) {
			t.Setenv("ALLOW_INSECURE_ISSUER", allow)
			for _, tc := range []struct {
				url   string
				valid bool
			}{
				{"https://issuer.example", true},
				{"http://localhost:8000", allow == "1"},
				{"http://127.0.0.1:8000", allow == "1"},
				{"http://[::1]:8000", allow == "1"},
				{"http://remote.example", false},
				{"https://user:password@issuer.example", false},
				{"https://issuer.example#fragment", false},
				{"", false},
			} {
				t.Run(tc.url, func(t *testing.T) {
					if err := TrustedURL(tc.url); (err == nil) != tc.valid {
						t.Fatalf("TrustedURL(%q) = %v, want valid=%v", tc.url, err, tc.valid)
					}
				})
			}
		})
	}
}

func TestHandlerBoundary(t *testing.T) {
	h, err := NewHandler(
		context.Background(),
		Config{Lab: 1, Resource: "http://localhost:8000/mcp"},
	)
	if err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct {
		name, path, origin string
		status             int
	}{
		{"healthy", "/healthz", "", http.StatusOK},
		{"untrusted origin", "/mcp", "https://evil.example", http.StatusForbidden},
		{"token in query", "/mcp?access_token=secret", "", http.StatusBadRequest},
	} {
		t.Run(tc.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, tc.path, nil)
			req.Header.Set("Origin", tc.origin)
			resp := httptest.NewRecorder()
			h.ServeHTTP(resp, req)
			if resp.Code != tc.status {
				t.Fatalf("status = %d, want %d; body: %s", resp.Code, tc.status, resp.Body.String())
			}
		})
	}
}
