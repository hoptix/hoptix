package handlers

import (
	"encoding/json"
	"io"
	"log"
	"net/http"

	"github.com/Strike-Bet/betting-engine/auth-service/service"
	"github.com/Strike-Bet/betting-engine/auth-service/types"
)

type AuthHandler struct {
	service *service.SupabaseAuthService
}

func NewAuthHandler(service *service.SupabaseAuthService) *AuthHandler {
	return &AuthHandler{service: service}
}

// GET /settings - Get public settings
func (h *AuthHandler) HandleSettings(w http.ResponseWriter, r *http.Request) {
	resp, err := h.service.MakeRequest("GET", "/settings", nil, false)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// POST /signup - Register a new user
func (h *AuthHandler) HandleSignup(w http.ResponseWriter, r *http.Request) {
	// Log the request for debugging
	log.Printf("Signup request: Method=%s, ContentType=%s, Origin=%s",
		r.Method, r.Header.Get("Content-Type"), r.Header.Get("Origin"))

	var req types.SignupRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		log.Printf("Signup request body decode error: %v", err)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{
			"error":   "Invalid request body",
			"details": err.Error(),
		})
		return
	}

	// Log the parsed request (without password)
	log.Printf("Signup request parsed: Email=%s, HasPassword=%t", req.Email, req.Password != "")

	resp, err := h.service.MakeRequest("POST", "/signup", req, false)
	if err != nil {
		log.Printf("Supabase request error: %v", err)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{
			"error":   "Internal server error",
			"details": err.Error(),
		})
		return
	}
	defer resp.Body.Close()

	log.Printf("Supabase response: Status=%d", resp.StatusCode)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// POST /token - OAuth2 token endpoint
func (h *AuthHandler) HandleToken(w http.ResponseWriter, r *http.Request) {
	grantType := r.URL.Query().Get("grant_type")

	if grantType == "password" {
		// Handle password grant
		var req struct {
			Email    string `json:"email,omitempty"`
			Phone    string `json:"phone,omitempty"`
			Password string `json:"password"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "Invalid request body", http.StatusBadRequest)
			return
		}

		endpoint := "/token?grant_type=password"
		resp, err := h.service.MakeRequest("POST", endpoint, req, false)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		defer resp.Body.Close()

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(resp.StatusCode)
		io.Copy(w, resp.Body)

	} else if grantType == "refresh_token" {
		// Handle refresh token grant
		var req struct {
			RefreshToken string `json:"refresh_token"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "Invalid request body", http.StatusBadRequest)
			return
		}

		endpoint := "/token?grant_type=refresh_token"
		resp, err := h.service.MakeRequest("POST", endpoint, req, false)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		defer resp.Body.Close()

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(resp.StatusCode)
		io.Copy(w, resp.Body)

	} else {
		http.Error(w, "Unsupported grant type. Use 'password' or 'refresh_token'", http.StatusBadRequest)
	}
}

// POST/GET /verify - Verify a user
func (h *AuthHandler) HandleVerify(w http.ResponseWriter, r *http.Request) {
	if r.Method == "GET" {
		h.handleVerifyGET(w, r)
	} else {
		h.handleVerifyPOST(w, r)
	}
}

func (h *AuthHandler) handleVerifyGET(w http.ResponseWriter, r *http.Request) {
	// Forward all query parameters
	endpoint := "/verify"
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

func (h *AuthHandler) handleVerifyPOST(w http.ResponseWriter, r *http.Request) {
	var req types.VerifyRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	resp, err := h.service.MakeRequest("POST", "/verify", req, false)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// POST /resend - Resend confirmation
func (h *AuthHandler) HandleResend(w http.ResponseWriter, r *http.Request) {
	var req map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	resp, err := h.service.MakeRequest("POST", "/resend", req, false)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// POST /recover - Password recovery
func (h *AuthHandler) HandleRecover(w http.ResponseWriter, r *http.Request) {
	var req types.RecoverRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	resp, err := h.service.MakeRequest("POST", "/recover", req, false)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// POST /magiclink - Send magic link
func (h *AuthHandler) HandleMagicLink(w http.ResponseWriter, r *http.Request) {
	var req types.MagicLinkRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	resp, err := h.service.MakeRequest("POST", "/magiclink", req, false)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// POST /otp - Send OTP
func (h *AuthHandler) HandleOTP(w http.ResponseWriter, r *http.Request) {
	var req types.OTPRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	resp, err := h.service.MakeRequest("POST", "/otp", req, false)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// POST /login-admin - Admin login with user verification
func (h *AuthHandler) HandleLoginAdmin(w http.ResponseWriter, r *http.Request) {
	var req types.LoginAdminRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		log.Printf("Admin login request body decode error: %v", err)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(types.ErrorResponse{
			Code:    http.StatusBadRequest,
			Message: "Invalid request body",
			Details: err.Error(),
		})
		return
	}

	log.Printf("Admin login attempt for email: %s", req.Email)

	// Step 1: Perform regular login
	loginReq := struct {
		Email    string `json:"email"`
		Password string `json:"password"`
	}{
		Email:    req.Email,
		Password: req.Password,
	}

	loginResp, err := h.service.MakeRequest("POST", "/token?grant_type=password", loginReq, false)
	if err != nil {
		log.Printf("Admin login - login request error: %v", err)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(types.ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "Login request failed",
			Details: err.Error(),
		})
		return
	}
	defer loginResp.Body.Close()

	// If login failed, return the error
	if loginResp.StatusCode != http.StatusOK {
		log.Printf("Admin login - login failed with status: %d", loginResp.StatusCode)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(loginResp.StatusCode)
		io.Copy(w, loginResp.Body)
		return
	}

	// Parse login response
	var authResponse types.AuthResponse
	loginBody, err := io.ReadAll(loginResp.Body)
	if err != nil {
		log.Printf("Admin login - failed to read login response: %v", err)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(types.ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "Failed to process login response",
			Details: err.Error(),
		})
		return
	}

	if err := json.Unmarshal(loginBody, &authResponse); err != nil {
		log.Printf("Admin login - failed to parse login response: %v", err)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(types.ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "Failed to parse login response",
			Details: err.Error(),
		})
		return
	}

	// Check if we have a user ID
	if authResponse.User == nil || authResponse.User.ID == "" {
		log.Printf("Admin login - no user ID in login response")
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(types.ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "No user ID found in login response",
		})
		return
	}

	userID := authResponse.User.ID
	log.Printf("Admin login - got user ID: %s", userID)

	// Step 2: Query user details from REST API
	endpoint := "/users?id=eq." + userID
	userResp, err := h.service.MakeRestRequest("GET", endpoint, nil, authResponse.AccessToken)
	if err != nil {
		log.Printf("Admin login - user details request error: %v", err)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(types.ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "Failed to fetch user details",
			Details: err.Error(),
		})
		return
	}
	defer userResp.Body.Close()

	if userResp.StatusCode != http.StatusOK {
		log.Printf("Admin login - user details request failed with status: %d", userResp.StatusCode)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(types.ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "Failed to fetch user details",
			Details: "User details API returned non-200 status",
		})
		return
	}

	// Parse user details response
	userBody, err := io.ReadAll(userResp.Body)
	if err != nil {
		log.Printf("Admin login - failed to read user details response: %v", err)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(types.ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "Failed to read user details response",
			Details: err.Error(),
		})
		return
	}

	var userDetails []types.AdminUserDetails
	if err := json.Unmarshal(userBody, &userDetails); err != nil {
		log.Printf("Admin login - failed to parse user details response: %v", err)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(types.ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "Failed to parse user details response",
			Details: err.Error(),
		})
		return
	}

	// Check if user was found
	if len(userDetails) == 0 {
		log.Printf("Admin login - user not found in database")
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(types.ErrorResponse{
			Code:    http.StatusNotFound,
			Message: "User not found in database",
		})
		return
	}

	// Check if user is admin
	adminUser := userDetails[0]
	if !adminUser.IsAdmin {
		log.Printf("Admin login - user %s is not an admin", req.Email)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusForbidden)
		json.NewEncoder(w).Encode(types.ErrorResponse{
			Code:    http.StatusForbidden,
			Message: "User is not an admin",
		})
		return
	}

	log.Printf("Admin login successful for: %s", req.Email)

	// Step 3: Combine responses
	adminResponse := types.LoginAdminResponse{
		AccessToken:  authResponse.AccessToken,
		TokenType:    authResponse.TokenType,
		ExpiresIn:    authResponse.ExpiresIn,
		ExpiresAt:    authResponse.ExpiresAt,
		RefreshToken: authResponse.RefreshToken,
		User:         authResponse.User,
		AdminDetails: &adminUser,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(adminResponse)
}
