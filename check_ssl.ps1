# Check SSL from Windows
try {
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}
    $wc = New-Object System.Net.WebClient
    $result = $wc.DownloadString("https://app.uvuv.xyz/")
    Write-Host "OK: " $result.Substring(0, [Math]::Min(100, $result.Length))
} catch {
    Write-Host "FAIL: " $_.Exception.Message
    Write-Host "Inner: " $_.Exception.InnerException
}
