[app]
title = VolleyBound
package.name = volleybound
package.domain = org.volleybound
source.dir = .
source.include_exts = py,png,jpg,jpeg,gif,ogg,wav,mp3
source.include_patterns = assets/*
source.main = main_android.py
version = 1.0
requirements = python3,pygame==2.1.4
orientation = landscape
fullscreen = 1
android.permissions = VIBRATE
android.api = 31
android.minapi = 21
android.archs = arm64-v8a

[buildozer]
log_level = 2