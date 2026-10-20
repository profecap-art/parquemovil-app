[app]
title = PME Conductor E2
package.name = pmeoposicion
package.domain = es.formacionvial
source.dir = .
source.include_exts = py,json,ttf,png
source.exclude_dirs = bin,.buildozer,__pycache__
version = 1.0.0
requirements = python3,kivy==2.3.1
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png
android.presplash_color = #1F4E8C
android.api = 34
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.ndk = 25b
p4a.branch = v2024.01.21
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 0
