// config/config.go
package config

import (
	"log"
	"os"
)

type Config struct {
	SupabaseURL    string // Your Supabase project URL
	SupabaseKey    string // Your Supabase anon key
	ServiceRoleKey string // Your Supabase service role key (for admin operations)
	JWTSecret      string // JWT secret for token validation
	Port           string
	Environment    string // development, staging, production
}

func Load() *Config {
	config := &Config{
		SupabaseURL:    getEnv("SUPABASE_URL", ""),
		SupabaseKey:    getEnv("SUPABASE_ANON_KEY", ""),
		ServiceRoleKey: getEnv("SUPABASE_SERVICE_ROLE_KEY", ""),
		JWTSecret:      getEnv("SUPABASE_JWT_SECRET", ""),
		Port:           getEnv("PORT", "8080"),
		Environment:    getEnv("ENVIRONMENT", "development"),
	}

	if config.SupabaseURL == "" {
		log.Fatal("SUPABASE_URL environment variable is required")
	}
	if config.SupabaseKey == "" {
		log.Fatal("SUPABASE_ANON_KEY environment variable is required")
	}
	if config.ServiceRoleKey == "" {
		log.Fatal("SUPABASE_SERVICE_ROLE_KEY environment variable is required")
	}
	if config.JWTSecret == "" {
		log.Fatal("SUPABASE_JWT_SECRET environment variable is required")
	}

	return config
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
