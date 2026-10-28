[app]
title = VolleyBound
package.name = volleybound
package.domain = org.volleybound
source.dir = .
source.include_exts = py,png,jpg,jpeg,gif,ogg,wav,mp3
source.include_patterns = assets/*
source.main = main_android.py
version = 1.0
requirements = python3,pygame
orientation = landscape
fullscreen = 1
android.permissions = VIBRATE
android.api = 33
android.minapi = 21
android.archs = arm64-v8a
p4a.source_dir = /home/runner/p4a

[buildozer]
log_level = 1