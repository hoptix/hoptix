package service

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"time"

	"github.com/Strike-Bet/betting-engine/auth-service/config"
)

type SupabaseAuthService struct {
	config     *config.Config
	httpClient *http.Client
	baseURL    string
}

func NewSupabaseAuthService(cfg *config.Config) *SupabaseAuthService {
	return &SupabaseAuthService{
		config:     cfg,
		httpClient: &http.Client{Timeout: 30 * time.Second},
		baseURL:    cfg.SupabaseURL + "/auth/v1",
	}
}

// MakeRequest makes an HTTP request to Supabase Auth API
func (s *SupabaseAuthService) MakeRequest(method, endpoint string, body interface{}, useServiceRole bool) (*http.Response, error) {
	var reqBody io.Reader

	if body != nil {
		jsonBody, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		reqBody = bytes.NewBuffer(jsonBody)
	}

	req, err := http.NewRequest(method, s.baseURL+endpoint, reqBody)
	if err != nil {
		return nil, err
	}

	// Set headers
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("apikey", s.config.SupabaseKey)

	if useServiceRole {
		req.Header.Set("Authorization", "Bearer "+s.config.ServiceRoleKey)
	}

	return s.httpClient.Do(req)
}

// MakeAuthenticatedRequest makes a request with user's access token
func (s *SupabaseAuthService) MakeAuthenticatedRequest(method, endpoint string, body interface{}, accessToken string) (*http.Response, error) {
	var reqBody io.Reader

	if body != nil {
		jsonBody, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		reqBody = bytes.NewBuffer(jsonBody)
	}

	req, err := http.NewRequest(method, s.baseURL+endpoint, reqBody)
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("apikey", s.config.SupabaseKey)
	req.Header.Set("Authorization", "Bearer "+accessToken)

	return s.httpClient.Do(req)
}

// MakeFormRequest makes a form-encoded request
func (s *SupabaseAuthService) MakeFormRequest(method, endpoint string, formData string) (*http.Response, error) {
	req, err := http.NewRequest(method, s.baseURL+endpoint, bytes.NewBufferString(formData))
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("apikey", s.config.SupabaseKey)

	return s.httpClient.Do(req)
}

// GetConfig returns the service configuration
func (s *SupabaseAuthService) GetConfig() *config.Config {
	return s.config
}

// MakeRestRequest makes an HTTP request to Supabase REST API
func (s *SupabaseAuthService) MakeRestRequest(method, endpoint string, body interface{}, accessToken string) (*http.Response, error) {
	var reqBody io.Reader

	if body != nil {
		jsonBody, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		reqBody = bytes.NewBuffer(jsonBody)
	}

	restURL := s.config.SupabaseURL + "/rest/v1" + endpoint
	req, err := http.NewRequest(method, restURL, reqBody)
	if err != nil {
		return nil, err
	}

	// Set headers for REST API
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("apikey", s.config.SupabaseKey)

	if accessToken != "" {
		req.Header.Set("Authorization", "Bearer "+accessToken)
	}

	return s.httpClient.Do(req)
}
