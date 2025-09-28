package handlers

import (
	"encoding/json"
	"io"
	"net/http"
	"strings"

	"github.com/Strike-Bet/betting-engine/auth-service/service"
	"github.com/Strike-Bet/betting-engine/auth-service/types"
)

type UserHandler struct {
	service *service.SupabaseAuthService
}

func NewUserHandler(service *service.SupabaseAuthService) *UserHandler {
	return &UserHandler{service: service}
}

// GET /user - Get current user (requires authentication)
func (h *UserHandler) HandleGetUser(w http.ResponseWriter, r *http.Request) {
	accessToken := extractAccessToken(r)
	if accessToken == "" {
		http.Error(w, "Authorization required", http.StatusUnauthorized)
		return
	}

	resp, err := h.service.MakeAuthenticatedRequest("GET", "/user", nil, accessToken)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// PUT /user - Update user (requires authentication)
func (h *UserHandler) HandleUpdateUser(w http.ResponseWriter, r *http.Request) {
	accessToken := extractAccessToken(r)
	if accessToken == "" {
		http.Error(w, "Authorization required", http.StatusUnauthorized)
		return
	}

	var req types.UpdateUserRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	resp, err := h.service.MakeAuthenticatedRequest("PUT", "/user", req, accessToken)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// POST /reauthenticate - Reauthenticate user
func (h *UserHandler) HandleReauthenticate(w http.ResponseWriter, r *http.Request) {
	accessToken := extractAccessToken(r)
	if accessToken == "" {
		http.Error(w, "Authorization required", http.StatusUnauthorized)
		return
	}

	resp, err := h.service.MakeAuthenticatedRequest("GET", "/reauthenticate", nil, accessToken)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// POST /logout - Logout user (requires authentication)
func (h *UserHandler) HandleLogout(w http.ResponseWriter, r *http.Request) {
	accessToken := extractAccessToken(r)
	if accessToken == "" {
		http.Error(w, "Authorization required", http.StatusUnauthorized)
		return
	}

	resp, err := h.service.MakeAuthenticatedRequest("POST", "/logout", nil, accessToken)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// extractAccessToken extracts the access token from Authorization header
func extractAccessToken(r *http.Request) string {
	authHeader := r.Header.Get("Authorization")
	if strings.HasPrefix(authHeader, "Bearer ") {
		return strings.TrimPrefix(authHeader, "Bearer ")
	}
	return ""
}
