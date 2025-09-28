package handlers

import (
	"io"
	"net/http"

	"github.com/Strike-Bet/betting-engine/auth-service/service"
)

type OAuthHandler struct {
	service *service.SupabaseAuthService
}

func NewOAuthHandler(service *service.SupabaseAuthService) *OAuthHandler {
	return &OAuthHandler{service: service}
}

// GET /authorize - OAuth2 authorization
func (h *OAuthHandler) HandleAuthorize(w http.ResponseWriter, r *http.Request) {
	// Forward all query parameters
	endpoint := "/authorize"
	if r.URL.RawQuery != "" {
		endpoint += "?" + r.URL.RawQuery
	}

	resp, err := h.service.MakeRequest("GET", endpoint, nil, false)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	// Handle redirect responses
	if resp.StatusCode == http.StatusSeeOther || resp.StatusCode == http.StatusFound {
		location := resp.Header.Get("Location")
		if location != "" {
			http.Redirect(w, r, location, resp.StatusCode)
			return
		}
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// GET /callback - OAuth2 callback
func (h *OAuthHandler) HandleCallback(w http.ResponseWriter, r *http.Request) {
	// Forward all query parameters
	endpoint := "/callback"
	if r.URL.RawQuery != "" {
		endpoint += "?" + r.URL.RawQuery
	}

	resp, err := h.service.MakeRequest("GET", endpoint, nil, false)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	// Handle redirect responses
	if resp.StatusCode == http.StatusSeeOther || resp.StatusCode == http.StatusFound {
		location := resp.Header.Get("Location")
		if location != "" {
			http.Redirect(w, r, location, resp.StatusCode)
			return
		}
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}
