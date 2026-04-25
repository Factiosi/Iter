# iter.factiosi.com — DNS и TLS

## 1. DNS у регистратора

- **A** для хоста `iter` → публичный IPv4 VPS.
- При наличии IPv6 — **AAAA** на тот же хост.

Проверка: `dig iter.factiosi.com A +short`

## 2. Systemd (API)

Пример unit-файла: [iter-api.service.example](iter-api.service.example). В `WorkingDirectory` и `EnvironmentFile` укажите путь **без пробелов** на сервере (или экранируйте путь в unit по правилам systemd).

## 3. Nginx

Актуальный прод (один порт uvicorn): [iter.factiosi.conf.example](iter.factiosi.conf.example) → **`/etc/nginx/sites-available/iter.factiosi`**.

Устаревший вариант (статика с диска + API на 8000): [nginx-iter.factiosi.com.conf.example](nginx-iter.factiosi.com.conf.example)

```bash
sudo cp iter.factiosi.conf.example /etc/nginx/sites-available/iter.factiosi
sudo ln -sf /etc/nginx/sites-available/iter.factiosi /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 4. Certbot (расширение существующего сертификата)

Если сертификат уже есть только на `factiosi.com` / `www`, добавьте `iter.factiosi.com` в SAN:

```bash
sudo certbot --nginx -d factiosi.com -d www.factiosi.com -d iter.factiosi.com
```

Если certbot предложит **expand** существующей цепочки — согласуйте (`--expand`).

Проверка:

```bash
sudo certbot certificates
curl -I https://iter.factiosi.com
```

Почта домена (MX для Mail.ru) настраивается **отдельно** для зоны `factiosi.com`, не для поддомена `iter`.
