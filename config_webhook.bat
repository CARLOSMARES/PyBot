# Configuración del Webhook de Meta (Messenger/Instagram)
curl -X POST "https://graph.facebook.com/v17.0/me/subscriptions" \
     -d "access_token=<TU_META_ACCESS_TOKEN>" \
     -d "object=page" \
     -d "callback_url=https://tu-dominio.com/webhook/meta" \
     -d "fields=messages,messaging_postbacks" \
     -d "verify_token=<TU_META_VERIFY_TOKEN>"