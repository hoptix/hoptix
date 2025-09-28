package handlers

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"

	"github.com/Strike-Bet/betting-engine/auth-service/service"
	"github.com/Strike-Bet/betting-engine/auth-service/types"

	"github.com/gorilla/mux"
)

type AdminHandler struct {
	service *service.SupabaseAuthService
}

func NewAdminHandler(service *service.SupabaseAuthService) *AdminHandler {
	return &AdminHandler{service: service}
}

// POST /admin/users - Create user (requires service role)
func (h *AdminHandler) HandleCreateUser(w http.ResponseWriter, r *http.Request) {
	var req types.AdminUserRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	resp, err := h.service.MakeRequest("POST", "/admin/users", req, true)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// PUT /admin/users/{user_id} - Update user (requires service role)
func (h *AdminHandler) HandleUpdateUser(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	userID := vars["user_id"]

	var req types.AdminUserRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	endpoint := fmt.Sprintf("/admin/users/%s", userID)
	resp, err := h.service.MakeRequest("PUT", endpoint, req, true)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// POST /admin/generate_link - Generate action link (requires service role)
func (h *AdminHandler) HandleGenerateLink(w http.ResponseWriter, r *http.Request) {
	var req types.GenerateLinkRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	resp, err := h.service.MakeRequest("POST", "/admin/generate_link", req, true)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// POST /invite - Invite a user (requires service role)
func (h *AdminHandler) HandleInvite(w http.ResponseWriter, r *http.Request) {
	var req types.InviteRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	resp, err := h.service.MakeRequest("POST", "/invite", req, true)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}
