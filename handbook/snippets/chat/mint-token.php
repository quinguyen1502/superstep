<?php
// Server only; $userId/$name come from your authenticated application user.
function mintChatToken($keyId, $secret, $slug, $userId, $name = '') {
    $b64 = function ($data) {
        return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
    };
    $encode = function ($value) use ($b64) {
        $json = json_encode($value, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        if ($json === false) {
            throw new RuntimeException('Cannot encode chat token');
        }
        return $b64($json);
    };
    $now = time();
    $header = $encode(['alg' => 'HS256', 'typ' => 'JWT', 'kid' => $keyId]);
    $claims = $encode(['iss' => $keyId, 'aud' => 'superstep-chat:' . $slug,
        'sub' => $userId, 'name' => $name, 'iat' => $now, 'exp' => $now + 600]);
    $unsigned = $header . '.' . $claims;
    return $unsigned . '.' . $b64(hash_hmac('sha256', $unsigned, $secret, true));
}
