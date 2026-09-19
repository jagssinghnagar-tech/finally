# Stop and remove the FinAlly container; db/ data is kept.
docker rm -f finally *> $null
Write-Host 'FinAlly stopped (data in ./db preserved)'
exit 0
