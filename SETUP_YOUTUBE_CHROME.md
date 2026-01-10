# Настройка YouTube downloads с Chrome profiles

## Как это работает

Bot работает в Docker контейнере, но **yt-dlp запускается НА ХОСТЕ** через SSH.
Это позволяет yt-dlp читать Chrome cookies через системный keyring!

## Шаги настройки на сервере

### 1. Установи yt-dlp на ХОСТ (не в Docker)

```bash
cd ~/CutClipAI
chmod +x install-host-ytdlp.sh
./install-host-ytdlp.sh
```

### 2. Запусти обновленный bot

```bash
cd ~/CutClipAI
git pull
docker-compose -f docker-compose.production.yml build bot
docker-compose -f docker-compose.production.yml up -d bot
```

### 3. Настрой SSH доступ из контейнера к хосту

```bash
# Получи публичный ключ из контейнера
docker-compose -f docker-compose.production.yml exec bot cat /root/.ssh/id_rsa.pub

# Добавь его в authorized_keys на хосте
docker-compose -f docker-compose.production.yml exec bot cat /root/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Проверь что SSH работает
docker-compose -f docker-compose.production.yml exec bot ssh -o StrictHostKeyChecking=no root@172.17.0.1 'echo SSH works!'
```

Если увидишь "SSH works!" - всё готово! ✅

### 4. Убедись что Chrome настроен на хосте

```bash
# Проверь что есть Chrome profiles
ls -la /root/.config/google-chrome/

# Должны быть директории: Default, Profile 3, Profile 26, и т.д.
# В каждой должен быть файл Cookies
```

### 5. Протестируй

Отправь боту age-restricted YouTube видео!

## Как проверить что работает

Смотри логи:

```bash
docker-compose -f docker-compose.production.yml logs -f bot
```

Если видишь:
```
INFO | Attempting download via HOST yt-dlp with profile: Default
INFO | HOST yt-dlp SUCCESS with profile Default
```

**ПОБЕДА!** 🎉

## Troubleshooting

### "Connection refused" или "Connection timed out"

```bash
# Убедись что SSH сервер запущен на хосте
systemctl status ssh
systemctl start ssh

# Проверь что порт 22 открыт
netstat -tlnp | grep :22
```

### "Permission denied (publickey)"

```bash
# Проверь authorized_keys
cat ~/.ssh/authorized_keys

# Добавь ключ из контейнера еще раз
docker-compose -f docker-compose.production.yml exec bot cat /root/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### "yt-dlp: command not found" на хосте

```bash
# Установи yt-dlp
pip3 install --upgrade yt-dlp

# Проверь
which yt-dlp
yt-dlp --version
```

