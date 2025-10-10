package main

import (
	"encoding/json"
	"log"
	"net/http"

	"github.com/Strike-Bet/betting-engine/auth-service/config"
	"github.com/Strike-Bet/betting-engine/auth-service/handlers"
	"github.com/Strike-Bet/betting-engine/auth-service/middleware"
	"github.com/Strike-Bet/betting-engine/auth-service/service"

	"github.com/gorilla/mux"
	"github.com/joho/godotenv"
)

func main() {
	// Load environment variables from .env file
	err := godotenv.Load()
	if err != nil {
		log.Printf("Warning: Error loading .env file: %v", err)
	}

	// Load configuration
	cfg := config.Load()

	// Create Supabase service
	supabaseService := service.NewSupabaseAuthService(cfg)

	// Create handlers
	authHandler := handlers.NewAuthHandler(supabaseService)
	userHandler := handlers.NewUserHandler(supabaseService)
	adminHandler := handlers.NewAdminHandler(supabaseService)
	oauthHandler := handlers.NewOAuthHandler(supabaseService)

	// Setup routes with middleware
	router := setupRoutes(cfg, authHandler, userHandler, adminHandler, oauthHandler)

	log.Printf("Supabase Auth Service starting on port %s", cfg.Port)
	log.Printf("Supabase URL: %s", cfg.SupabaseURL)
	log.Printf("Environment: %s", cfg.Environment)

	log.Fatal(http.ListenAndServe(":"+cfg.Port, router))
}

func setupRoutes(
	cfg *config.Config,
	authHandler *handlers.AuthHandler,
	userHandler *handlers.UserHandler,
	adminHandler *handlers.AdminHandler,
	oauthHandler *handlers.OAuthHandler,
) *mux.Router {
	router := mux.NewRouter()

	// Apply global middleware
	router.Use(middleware.CORSMiddleware())
	router.Use(middleware.LoggingMiddleware())
	router.Use(middleware.SecurityHeadersMiddleware())
	router.Use(middleware.JSONContentTypeMiddleware())
	router.Use(middleware.RateLimitMiddleware())

	// Health check endpoint (unprotected)
	router.HandleFunc("/health", handleHealth).Methods("GET")

	// Public auth endpoints (no authentication required)
	setupPublicRoutes(router, authHandler, oauthHandler)

	// Protected user endpoints (requires valid JWT token)
	setupProtectedRoutes(router, cfg, userHandler)

	// Admin endpoints (requires service role or admin privileges)
	setupAdminRoutes(router, cfg, adminHandler)

	// Debug endpoints (only in development)
	if cfg.Environment == "development" {
		setupDebugRoutes(router, cfg)
	}

	return router
}

func setupPublicRoutes(router *mux.Router, authHandler *handlers.AuthHandler, oauthHandler *handlers.OAuthHandler) {
	// Public auth endpoints
	router.HandleFunc("/settings", authHandler.HandleSettings).Methods("GET")
	router.HandleFunc("/signup", authHandler.HandleSignup).Methods("POST")
	router.HandleFunc("/token", authHandler.HandleToken).Methods("POST")
	router.HandleFunc("/verify", authHandler.HandleVerify).Methods("GET", "POST")
	router.HandleFunc("/resend", authHandler.HandleResend).Methods("POST")
	router.HandleFunc("/recover", authHandler.HandleRecover).Methods("POST")
	router.HandleFunc("/magiclink", authHandler.HandleMagicLink).Methods("POST")
	router.HandleFunc("/otp", authHandler.HandleOTP).Methods("POST")

	// OAuth endpoints
	router.HandleFunc("/authorize", oauthHandler.HandleAuthorize).Methods("GET")
	router.HandleFunc("/callback", oauthHandler.HandleCallback).Methods("GET")

	// Handle all OPTIONS requests for CORS preflight
	router.PathPrefix("/").HandlerFunc(handleOptions).Methods("OPTIONS")
}

func setupProtectedRoutes(router *mux.Router, cfg *config.Config, userHandler *handlers.UserHandler) {
	// Protected user endpoints (requires valid JWT token)
	protectedUser := router.PathPrefix("").Subrouter()
	protectedUser.Use(middleware.AuthMiddleware(cfg))

	protectedUser.HandleFunc("/user", userHandler.HandleGetUser).Methods("GET")
	protectedUser.HandleFunc("/user", userHandler.HandleUpdateUser).Methods("PUT")
	protectedUser.HandleFunc("/reauthenticate", userHandler.HandleReauthenticate).Methods("GET")
	protectedUser.HandleFunc("/logout", userHandler.HandleLogout).Methods("POST")
}

func setupAdminRoutes(router *mux.Router, cfg *config.Config, adminHandler *handlers.AdminHandler) {
	// Admin endpoints (requires service role or admin privileges)
	adminRoutes := router.PathPrefix("/admin").Subrouter()
	adminRoutes.Use(middleware.AdminMiddleware(cfg))

	adminRoutes.HandleFunc("/users", adminHandler.HandleCreateUser).Methods("POST")
	adminRoutes.HandleFunc("/users/{user_id}", adminHandler.HandleUpdateUser).Methods("PUT")
	adminRoutes.HandleFunc("/generate_link", adminHandler.HandleGenerateLink).Methods("POST")

	// Invite endpoint (requires admin privileges)
	inviteRoutes := router.PathPrefix("").Subrouter()
	inviteRoutes.Use(middleware.AdminMiddleware(cfg))
	inviteRoutes.HandleFunc("/invite", adminHandler.HandleInvite).Methods("POST")
}

func setupDebugRoutes(router *mux.Router, cfg *config.Config) {
	// Debug endpoints (only in development)
	debugRoutes := router.PathPrefix("/debug").Subrouter()
	debugRoutes.Use(middleware.AuthMiddleware(cfg))

	debugRoutes.HandleFunc("/token", handleDebugToken).Methods("GET")
	debugRoutes.HandleFunc("/config", handleDebugConfig(cfg)).Methods("GET")
}

// Health check handler
func handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":    "healthy",
		"service":   "supabase-auth-service",
		"version":   "1.0.0",
		"timestamp": "2025-05-30T00:00:00Z",
	})
}

// Debug token handler
func handleDebugToken(w http.ResponseWriter, r *http.Request) {
	user := middleware.GetUserFromContext(r)
	if user == nil {
		http.Error(w, "No user in context", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"user_id": user.UserID,
		"email":   user.Email,
		"role":    user.Role,
		"claims":  user,
	})
}

// Debug config handler
func handleDebugConfig(cfg *config.Config) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"environment":     cfg.Environment,
			"port":            cfg.Port,
			"supabase_url":    cfg.SupabaseURL,
			"has_jwt_secret":  cfg.JWTSecret != "",
			"has_service_key": cfg.ServiceRoleKey != "",
		})
	}
}

// OPTIONS handler for CORS preflight requests
func handleOptions(w http.ResponseWriter, r *http.Request) {
	// CORS headers are already set by CORSMiddleware
	w.WriteHeader(http.StatusOK)
}
