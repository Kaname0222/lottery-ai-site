$proc = Start-Process -FilePath "uvicorn" -ArgumentList "app.main:app --host 0.0.0.0 --port 8001" -WorkingDirectory "c:\Users\19692\Desktop\test\lottery-ai-site\backend" -RedirectStandardOutput "c:\Users\19692\Desktop\test\lottery-ai-site\backend\test_server.log" -RedirectStandardError "c:\Users\19692\Desktop\test\lottery-ai-site\backend\test_server_err.log" -PassThru
Start-Sleep -Seconds 5
Write-Output $proc.Id
