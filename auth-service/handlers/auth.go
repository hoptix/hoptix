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

		// If login failed, return the error as-is
		if resp.StatusCode != http.StatusOK {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(resp.StatusCode)
			io.Copy(w, resp.Body)
			return
		}

		// Parse the auth response to check admin status
		var authResponse types.AuthResponse
		responseBody, err := io.ReadAll(resp.Body)
		if err != nil {
			log.Printf("Failed to read token response: %v", err)
			http.Error(w, "Failed to process authentication response", http.StatusInternalServerError)
			return
		}

		if err := json.Unmarshal(responseBody, &authResponse); err != nil {
			log.Printf("Failed to parse token response: %v", err)
			http.Error(w, "Failed to parse authentication response", http.StatusInternalServerError)
			return
		}

		// Check admin status from public.users table
		isAdmin := false
		if authResponse.User != nil && authResponse.User.ID != "" {
			userEndpoint := "/users?id=eq." + authResponse.User.ID + "&select=is_admin"
			userResp, err := h.service.MakeRestRequest("GET", userEndpoint, nil, authResponse.AccessToken)
			if err == nil {
				defer userResp.Body.Close()
				if userResp.StatusCode == http.StatusOK {
					var users []struct {
						IsAdmin bool `json:"is_admin"`
					}
					userBody, err := io.ReadAll(userResp.Body)
					if err == nil {
						if err := json.Unmarshal(userBody, &users); err == nil && len(users) > 0 {
							isAdmin = users[0].IsAdmin
						}
					}
				}
			}
		}

		// Add is_admin to response
		authResponse.IsAdmin = isAdmin
		if authResponse.User != nil {
			authResponse.User.IsAdmin = isAdmin
		}

		// Return the modified response
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(authResponse)

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

		// If refresh failed, return the error as-is
		if resp.StatusCode != http.StatusOK {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(resp.StatusCode)
			io.Copy(w, resp.Body)
			return
		}

		// Parse the auth response to check admin status
		var authResponse types.AuthResponse
		responseBody, err := io.ReadAll(resp.Body)
		if err != nil {
			log.Printf("Failed to read refresh token response: %v", err)
			http.Error(w, "Failed to process refresh response", http.StatusInternalServerError)
			return
		}

		if err := json.Unmarshal(responseBody, &authResponse); err != nil {
			log.Printf("Failed to parse refresh token response: %v", err)
			http.Error(w, "Failed to parse refresh response", http.StatusInternalServerError)
			return
		}

		// Check admin status from public.users table
		isAdmin := false
		if authResponse.User != nil && authResponse.User.ID != "" {
			userEndpoint := "/users?id=eq." + authResponse.User.ID + "&select=is_admin"
			userResp, err := h.service.MakeRestRequest("GET", userEndpoint, nil, authResponse.AccessToken)
			if err == nil {
				defer userResp.Body.Close()
				if userResp.StatusCode == http.StatusOK {
					var users []struct {
						IsAdmin bool `json:"is_admin"`
					}
					userBody, err := io.ReadAll(userResp.Body)
					if err == nil {
						if err := json.Unmarshal(userBody, &users); err == nil && len(users) > 0 {
							isAdmin = users[0].IsAdmin
						}
					}
				}
			}
		}

		// Add is_admin to response
		authResponse.IsAdmin = isAdmin
		if authResponse.User != nil {
			authResponse.User.IsAdmin = isAdmin
		}

		// Return the modified response
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(authResponse)

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

