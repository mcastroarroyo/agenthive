/**
 * Mail relay for the Agent Hive showcase (Google Apps Script web app).
 *
 * The showcase web app (Cloud Run) POSTs {id_token, to, subject, html}. The relay only sends when the Google ID token
 * belongs to the service account in script property CALLER and was minted for AUDIENCE (this web app's /exec URL),
 * and only to addresses listed in RECIPIENTS. No shared secret: identity comes from Google.
 *
 * Setup: new Apps Script project -> paste this file -> Project Settings -> Script properties:
 *   CALLER      agenthive-showcase-web@<project>.iam.gserviceaccount.com
 *   RECIPIENTS  admin1@example.com,admin2@example.com
 *   AUDIENCE    https://script.google.com/macros/s/<deployment id>/exec   (after the first deployment)
 * Deploy -> New deployment -> Web app -> Execute as: Me, Who has access: Anyone -> authorise -> copy the /exec URL
 * into HIVE_MAIL_RELAY (Cloud Run) and AUDIENCE (here).
 */
function doPost(e) {
  var props = PropertiesService.getScriptProperties();
  var caller = (props.getProperty('CALLER') || '').toLowerCase();
  var audience = props.getProperty('AUDIENCE') || '';
  var allowed = (props.getProperty('RECIPIENTS') || '').split(',')
    .map(function (s) { return s.trim().toLowerCase(); }).filter(String);
  var req;
  try { req = JSON.parse(e.postData.contents); } catch (err) { return out_({ ok: false, error: 'bad request' }); }
  var who = verify_(req.id_token);
  if (!who || who.email.toLowerCase() !== caller || who.aud !== audience) return out_({ ok: false, error: 'forbidden' });
  var to = (req.to || []).map(function (s) { return String(s).toLowerCase(); })
    .filter(function (s) { return allowed.indexOf(s) >= 0; });
  if (!to.length) return out_({ ok: false, error: 'no allowed recipients' });
  MailApp.sendEmail({ to: to.join(','), subject: String(req.subject || '').slice(0, 200),
                      htmlBody: String(req.html || '').slice(0, 50000), name: 'Wursta Agent Hive' });
  return out_({ ok: true, sent: to.length });
}

function verify_(token) {
  if (!token) return null;
  var r = UrlFetchApp.fetch('https://oauth2.googleapis.com/tokeninfo?id_token=' + encodeURIComponent(token),
                            { muteHttpExceptions: true });
  if (r.getResponseCode() !== 200) return null;
  var info = JSON.parse(r.getContentText());
  if (!info.email || info.email_verified === 'false' || Number(info.exp) * 1000 < Date.now()) return null;
  return info;
}

function out_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
