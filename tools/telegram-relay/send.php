<?php
// Релей заявок sd-kt.ru → Telegram-группа (хостинг Reg.ru, api.sd-kt.ru).
// Токен и chat_id — в tg_config.php РЯДОМ НА СЕРВЕРЕ (в репозиторий не попадает,
// образец — tg_config.example.php, доступ снаружи закрыт через .htaccess).
require __DIR__ . '/tg_config.php';

$origin  = $_SERVER['HTTP_ORIGIN'] ?? '';
$allowed = ['https://sd-kt.ru', 'https://www.sd-kt.ru'];
header('Access-Control-Allow-Origin: ' . (in_array($origin, $allowed, true) ? $origin : 'https://sd-kt.ru'));
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if (($_SERVER['REQUEST_METHOD'] ?? '') === 'OPTIONS') { http_response_code(204); exit; }
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST')   { echo 'SYNDICAT relay: OK'; exit; }

$fields = $_POST;
if (!$fields) {
    $json = json_decode(file_get_contents('php://input'), true);
    if (is_array($json)) $fields = $json;
}

// скрытое поле-приманка: человек его не заполняет, спам-бот заполнит
if (!empty($fields['_gotcha'])) {
    header('Content-Type: application/json');
    echo '{"ok":true}';
    exit;
}

$rows = [];
foreach ($fields as $k => $v) {
    if (strpos($k, '_') === 0 || !is_scalar($v)) continue;
    $v = trim((string)$v);
    if ($v === '') continue;
    $rows[] = '<b>' . htmlspecialchars($k, ENT_QUOTES, 'UTF-8') . ':</b> '
            . htmlspecialchars(mb_substr($v, 0, 800), ENT_QUOTES, 'UTF-8');
}
$text = "\u{1F514} <b>Заявка с сайта sd-kt.ru</b>\n" . ($rows ? implode("\n", $rows) : '(пустая форма)');

$ch = curl_init('https://api.telegram.org/bot' . TG_TOKEN . '/sendMessage');
curl_setopt_array($ch, [
    CURLOPT_POST           => true,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT        => 10,
    CURLOPT_POSTFIELDS     => http_build_query([
        'chat_id'    => TG_CHAT_ID,
        'text'       => $text,
        'parse_mode' => 'HTML',
    ]),
]);
$resp = curl_exec($ch);
$ok   = $resp !== false && strpos($resp, '"ok":true') !== false;
curl_close($ch);

// если форму отправили напрямую (без JS) — вернуть человека на страницу «спасибо»
if (strpos($_SERVER['HTTP_ACCEPT'] ?? '', 'text/html') !== false) {
    header('Location: https://sd-kt.ru/thanks.html', true, 302);
    exit;
}
header('Content-Type: application/json');
echo json_encode(['ok' => $ok]);
