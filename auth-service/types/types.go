package types

import "time"

// User represents a user from Supabase Auth
type User struct {
	ID                 string                 `json:"id"`
	Aud                string                 `json:"aud"`
	Role               string                 `json:"role"`
	Email              string                 `json:"email"`
	Phone              string                 `json:"phone"`
	EmailConfirmedAt   *time.Time             `json:"email_confirmed_at"`
	PhoneConfirmedAt   *time.Time             `json:"phone_confirmed_at"`
	ConfirmationSentAt *time.Time             `json:"confirmation_sent_at"`
	RecoverySentAt     *time.Time             `json:"recovery_sent_at"`
	EmailChangeSentAt  *time.Time             `json:"email_change_sent_at"`
	PhoneChangeSentAt  *time.Time             `json:"phone_change_sent_at"`
	CreatedAt          time.Time              `json:"created_at"`
	UpdatedAt          time.Time              `json:"updated_at"`
	LastSignInAt       *time.Time             `json:"last_sign_in_at"`
	UserMetadata       map[string]interface{} `json:"user_metadata"`
	AppMetadata        map[string]interface{} `json:"app_metadata"`
	Identities         []Identity             `json:"identities"`
}

type Identity struct {
	ID           string                 `json:"id"`
	UserID       string                 `json:"user_id"`
	Provider     string                 `json:"provider"`
	IdentityData map[string]interface{} `json:"identity_data"`
	CreatedAt    time.Time              `json:"created_at"`
	UpdatedAt    time.Time              `json:"updated_at"`
}

// Request types
type SignupRequest struct {
	Email    string                 `json:"email,omitempty"`
	Phone    string                 `json:"phone,omitempty"`
	Password string                 `json:"password"`
	Data     map[string]interface{} `json:"data,omitempty"`
}

type LoginRequest struct {
	Email    string `json:"email,omitempty"`
	Phone    string `json:"phone,omitempty"`
	Password string `json:"password"`
}

type TokenRequest struct {
	GrantType    string `json:"grant_type"`
	Email        string `json:"email,omitempty"`
	Phone        string `json:"phone,omitempty"`
	Password     string `json:"password,omitempty"`
	RefreshToken string `json:"refresh_token,omitempty"`
}

type VerifyRequest struct {
	Type       string `json:"type"`
	Token      string `json:"token"`
	Email      string `json:"email,omitempty"`
	Phone      string `json:"phone,omitempty"`
	RedirectTo string `json:"redirect_to,omitempty"`
}

type RecoverRequest struct {
	Email string `json:"email"`
}

type MagicLinkRequest struct {
	Email      string `json:"email"`
	CreateUser bool   `json:"create_user,omitempty"`
}

type OTPRequest struct {
	Email      string `json:"email,omitempty"`
	Phone      string `json:"phone,omitempty"`
	CreateUser bool   `json:"create_user,omitempty"`
}

type UpdateUserRequest struct {
	Email    string                 `json:"email,omitempty"`
	Phone    string                 `json:"phone,omitempty"`
	Password string                 `json:"password,omitempty"`
	Data     map[string]interface{} `json:"data,omitempty"`
	Nonce    string                 `json:"nonce,omitempty"`
}

type InviteRequest struct {
	Email string                 `json:"email"`
	Data  map[string]interface{} `json:"data,omitempty"`
}

type AdminUserRequest struct {
	Role         string                 `json:"role,omitempty"`
	Email        string                 `json:"email,omitempty"`
	Phone        string                 `json:"phone,omitempty"`
	Password     string                 `json:"password,omitempty"`
	EmailConfirm bool                   `json:"email_confirm,omitempty"`
	PhoneConfirm bool                   `json:"phone_confirm,omitempty"`
	UserMetadata map[string]interface{} `json:"user_metadata,omitempty"`
	AppMetadata  map[string]interface{} `json:"app_metadata,omitempty"`
	BanDuration  string                 `json:"ban_duration,omitempty"`
}

type GenerateLinkRequest struct {
	Type       string                 `json:"type"` // "signup", "magiclink", "recovery", "invite"
	Email      string                 `json:"email"`
	Password   string                 `json:"password,omitempty"`
	Data       map[string]interface{} `json:"data,omitempty"`
	RedirectTo string                 `json:"redirect_to,omitempty"`
}

// Response types
type AuthResponse struct {
	AccessToken  string `json:"access_token"`
	TokenType    string `json:"token_type"`
	ExpiresIn    int    `json:"expires_in"`
	ExpiresAt    int64  `json:"expires_at"`
	RefreshToken string `json:"refresh_token"`
	User         *User  `json:"user"`
}

type GenerateLinkResponse struct {
	ActionLink       string `json:"action_link"`
	EmailOTP         string `json:"email_otp"`
	HashedToken      string `json:"hashed_token"`
	VerificationType string `json:"verification_type"`
	RedirectTo       string `json:"redirect_to"`
}

type SettingsResponse struct {
	External      map[string]bool `json:"external"`
	DisableSignup bool            `json:"disable_signup"`
	AutoConfirm   bool            `json:"autoconfirm"`
}

type ErrorResponse struct {
	Code    int    `json:"code"`
	Message string `json:"msg"`
	Details string `json:"details,omitempty"`
}

type ReauthRequest struct {
	Nonce string `json:"nonce,omitempty"`
}

// Admin login types
type LoginAdminRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type AdminUserDetails struct {
	ID        string    `json:"id"`
	Email     string    `json:"email"`
	IsAdmin   bool      `json:"is_admin"`
	CreatedAt time.Time `json:"created_at"`
}

type LoginAdminResponse struct {
	AccessToken  string            `json:"access_token"`
	TokenType    string            `json:"token_type"`
	ExpiresIn    int               `json:"expires_in"`
	ExpiresAt    int64             `json:"expires_at"`
	RefreshToken string            `json:"refresh_token"`
	User         *User             `json:"user"`
	AdminDetails *AdminUserDetails `json:"admin_details"`
}
