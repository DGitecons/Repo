@echo off
rem Espera 20 segundos antes de começar
timeout /t 20 > nul

rem Inicia o XAMPP em segundo plano
start /min "" "C:\xampp\xampp-control.exe"
rem Espera mais tempo para garantir que o XAMPP esteja totalmente iniciado
timeout /t 30 > nul

rem Executa o script Python pela primeira vez em segundo plano
start /B python "C:\xampp\htdocs\Code\1webscrapper_F.py"

rem Executa o navegador Chrome no modo kiosk (sem interface) no monitor secundário (1920x1080)
start chrome --kiosk --window-position=1366,0 http://localhost/Code/main_F.html

rem Loop para executar o script Python a cada minuto
:loop
rem Executa o script Python em segundo plano
start /B python "C:\xampp\htdocs\Code\1webscrapper_F.py"
timeout /t 43200 > nul

rem Volta ao início do loop
goto loop
