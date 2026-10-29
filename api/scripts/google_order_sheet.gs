/**
 * Apps Script web app for TAPTOT.
 *
 * Feedback (no kind, or kind other than "order") still appends a row on tab "Góp ý".
 * Orders (kind === "order") upsert a row on tab "Đơn hàng" by column "Mã đơn".
 *
 * Script properties: SHEETS_SECRET = same value as ORDER_SHEETS_SECRET / FEEDBACK_SHEETS_SECRET.
 * Deploy as Web app, execute as you, anyone with the link. Paste the /exec URL into
 * ORDER_SHEETS_WEBHOOK_URL (and FEEDBACK_SHEETS_WEBHOOK_URL if this replaces the old script).
 */
var ORDER_HEADERS = [
  "Thời gian",
  "Mã đơn",
  "Trạng thái",
  "Người nhận",
  "SĐT",
  "Địa chỉ",
  "Sản phẩm",
  "Tổng tiền",
  "Giảm thử thách",
  "Mã giảm giá",
  "Đã giảm mã",
  "Thanh toán",
  "Ghi chú",
];

function doPost(e) {
  var body = JSON.parse(e.postData.contents || "{}");
  var secret = PropertiesService.getScriptProperties().getProperty("SHEETS_SECRET") || "";
  if (secret && body.secret !== secret) {
    return json_({ ok: false, error: "unauthorized" });
  }
  if (body.kind === "order") {
    upsertOrder_(body);
  } else {
    appendFeedback_(body);
  }
  return json_({ ok: true });
}

function upsertOrder_(body) {
  var sheet = SpreadsheetApp.getActive().getSheetByName("Đơn hàng");
  if (!sheet) {
    sheet = SpreadsheetApp.getActive().insertSheet("Đơn hàng");
  }
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(ORDER_HEADERS);
  }
  var code = String(body.public_code || "");
  var values = [
    body.time || "",
    code,
    body.status || "",
    body.recipient_name || "",
    body.phone || "",
    body.address || "",
    body.products || "",
    body.total_vnd || 0,
    body.discount_vnd || 0,
    body.promo_code || "",
    body.promo_discount_vnd || 0,
    body.payment || "",
    body.note || "",
  ];
  var row = findOrderRow_(sheet, code);
  if (row > 0) {
    sheet.getRange(row, 1, 1, values.length).setValues([values]);
  } else {
    sheet.appendRow(values);
  }
}

function findOrderRow_(sheet, code) {
  if (!code) return 0;
  var last = sheet.getLastRow();
  if (last < 2) return 0;
  var codes = sheet.getRange(2, 2, last - 1, 1).getValues();
  for (var i = 0; i < codes.length; i++) {
    if (String(codes[i][0]) === code) return i + 2;
  }
  return 0;
}

function appendFeedback_(body) {
  var sheet = SpreadsheetApp.getActive().getSheetByName("Góp ý");
  if (!sheet) {
    sheet = SpreadsheetApp.getActive().insertSheet("Góp ý");
    sheet.appendRow(["Thời gian", "Email", "Chủ đề", "Link lịch", "Nội dung"]);
  }
  sheet.appendRow([
    body.time || "",
    body.email || "",
    body.category || "",
    body.plan_url || "",
    body.content || "",
  ]);
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
