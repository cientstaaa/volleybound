[app]
title = VolleyBound
package.name = volleybound
package.domain = org.volleybound
source.dir = .
source.include_exts = py,png,jpg,jpeg,gif,ogg,wav,mp3
source.include_patterns = assets/*,*.py
source.main = main_android.py
version = 1.0
requirements = python3,pygame
orientation = landscape
fullscreen = 1
android.permissions = VIBRATE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
p4a.branch = master

[buildozer]
log_level = 2