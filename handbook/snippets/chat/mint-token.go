package chatmint

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"time"
)

// Server only; userID/name come from your authenticated application user.
func MintChatToken(keyID, secret, slug, userID, name string) (string, error) {
	encode := func(value any) (string, error) {
		data, err := json.Marshal(value)
		return base64.RawURLEncoding.EncodeToString(data), err
	}
	now := time.Now().Unix()
	header, err := encode(map[string]any{"alg": "HS256", "typ": "JWT", "kid": keyID})
	if err != nil {
		return "", err
	}
	claims, err := encode(map[string]any{"iss": keyID, "aud": "superstep-chat:" + slug,
		"sub": userID, "name": name, "iat": now, "exp": now + 600})
	if err != nil {
		return "", err
	}
	unsigned := header + "." + claims
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(unsigned))
	return unsigned + "." + base64.RawURLEncoding.EncodeToString(mac.Sum(nil)), nil
}
