// middleware/auth.go
package middleware

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"

	"github.com/Strike-Bet/betting-engine/auth-service/config"
	"github.com/golang-jwt/jwt/v5"
	"github.com/gorilla/mux"
)

// Custom context keys
type contextKey string

const (
	UserContextKey  contextKey = "user"
	TokenContextKey contextKey = "token"
)

// User claims from JWT
type UserClaims struct {
	UserID   string                 `json:"sub"`
	Email    string                 `json:"email,omitempty"`
	Phone    string                 `json:"phone,omitempty"`
	Role     string                 `json:"role"`
	Metadata map[string]interface{} `json:"user_metadata,omitempty"`
	jwt.RegisteredClaims
}

// ErrorResponse for middleware errors
type ErrorResponse struct {
	Code    int    `json:"code"`
	Message string `json:"msg"`
	Details string `json:"details,omitempty"`
}

// Authentication middleware - validates JWT tokens
func AuthMiddleware(cfg *config.Config) mux.MiddlewareFunc {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			// Extract token from Authorization header
			authHeader := r.Header.Get("Authorization")
			if authHeader == "" {
				writeError(w, http.StatusUnauthorized, "Missing authorization header")
				return
			}

			// Check Bearer token format
			tokenParts := strings.Split(authHeader, " ")
			if len(tokenParts) != 2 || tokenParts[0] != "Bearer" {
				writeError(w, http.StatusUnauthorized, "Invalid authorization header format")
				return
			}

			tokenString := tokenParts[1]

			// Parse and validate JWT token
			token, err := jwt.ParseWithClaims(tokenString, &UserClaims{}, func(token *jwt.Token) (interface{}, error) {
				// Validate signing method
				if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
					return nil, jwt.ErrSignatureInvalid
				}
				return []byte(cfg.JWTSecret), nil
			})

			if err != nil {
				writeError(w, http.StatusUnauthorized, "Invalid token: "+err.Error())
				return
			}

			if !token.Valid {
				writeError(w, http.StatusUnauthorized, "Token is not valid")
				return
			}

			// Extract claims
			claims, ok := token.Claims.(*UserClaims)
			if !ok {
				writeError(w, http.StatusUnauthorized, "Invalid token claims")
				return
			}

			// Add user info to request context
			ctx := context.WithValue(r.Context(), UserContextKey, claims)
			ctx = context.WithValue(ctx, TokenContextKey, tokenString)

			// Continue to next handler
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// Admin middleware - requires service role or admin privileges
func AdminMiddleware(cfg *config.Config) mux.MiddlewareFunc {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			// Extract token from Authorization header
			authHeader := r.Header.Get("Authorization")
			if authHeader == "" {
				writeError(w, http.StatusUnauthorized, "Missing authorization header")
				return
			}

			tokenParts := strings.Split(authHeader, " ")
			if len(tokenParts) != 2 || tokenParts[0] != "Bearer" {
				writeError(w, http.StatusUnauthorized, "Invalid authorization header format")
				return
			}

			tokenString := tokenParts[1]

			// Check if it's the service role key
			if tokenString == cfg.ServiceRoleKey {
				// Service role has full admin access
				ctx := context.WithValue(r.Context(), TokenContextKey, tokenString)
				next.ServeHTTP(w, r.WithContext(ctx))
				return
			}

			// Otherwise, validate as regular JWT and check for admin role
			token, err := jwt.ParseWithClaims(tokenString, &UserClaims{}, func(token *jwt.Token) (interface{}, error) {
				if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
					return nil, jwt.ErrSignatureInvalid
				}
				return []byte(cfg.JWTSecret), nil
			})

			if err != nil {
				writeError(w, http.StatusForbidden, "Invalid admin token: "+err.Error())
				return
			}

			if !token.Valid {
				writeError(w, http.StatusForbidden, "Admin token is not valid")
				return
			}

			claims, ok := token.Claims.(*UserClaims)
			if !ok {
				writeError(w, http.StatusForbidden, "Invalid admin token claims")
				return
			}

			// Check if user has admin role
			if claims.Role != "admin" && claims.Role != "service_role" {
				writeError(w, http.StatusForbidden, "Admin privileges required")
				return
			}

			// Add user info to request context
			ctx := context.WithValue(r.Context(), UserContextKey, claims)
			ctx = context.WithValue(ctx, TokenContextKey, tokenString)

			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// Helper function to write error responses
func writeError(w http.ResponseWriter, statusCode int, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)

	errorResp := ErrorResponse{
		Code:    statusCode,
		Message: message,
	}

	json.NewEncoder(w).Encode(errorResp)
}

// Helper functions to extract user info from context (for use in handlers)
func GetUserFromContext(r *http.Request) *UserClaims {
	if user := r.Context().Value(UserContextKey); user != nil {
		return user.(*UserClaims)
	}
	return nil
}

func GetTokenFromContext(r *http.Request) string {
	if token := r.Context().Value(TokenContextKey); token != nil {
		return token.(string)
	}
	return ""
}
