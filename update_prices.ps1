# -*- coding: utf-8 -*-
# 네이버 금융 시세 수집기 (PowerShell 버전 - 야후 파이낸스 제외, 네이버 증권 100% 실시간 연동)

$SUPABASE_URL = "https://wlavetbnglzrpkeyesqv.supabase.co"
$SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndsYXZldGJuZ2x6cnBrZXllc3F2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg1NDQ1MTMsImV4cCI6MjEwNDEyMDUxM30.1hk6OBMoqTcpUHEVxjXlIfr1SKf776sa-65xPPSy35M"

$headers = @{
    "apikey" = $SUPABASE_KEY
    "Authorization" = "Bearer $SUPABASE_KEY"
    "Content-Type" = "application/json; charset=utf-8"
    "Prefer" = "resolution=merge-duplicates"
}

function Normalize-Ticker($t) {
    if (-not $t) { return "" }
    $clean = $t.Trim().ToUpper()
    if ($clean.StartsWith("O") -and $clean.Length -eq 6) {
        $clean = "0" + $clean.Substring(1)
    }
    return $clean
}

# 1. 대상 티커 수집
$tickers = [System.Collections.Generic.HashSet[string]]::new()
$defaultTickers = @("0198A0", "0219E0", "441680", "486290", "458730", "482730", "JEPQ", "JEPI", "TSLY", "CONY", "NVDY")
foreach ($dt in $defaultTickers) {
    [void]$tickers.Add((Normalize-Ticker $dt))
}

$rawTickerMap = @{}

try {
    $txUrl = "$SUPABASE_URL/rest/v1/transactions?select=ticker"
    $txList = Invoke-RestMethod -Uri $txUrl -Headers $headers
    foreach ($row in $txList) {
        $orig = $row.ticker.Trim().ToUpper()
        $norm = Normalize-Ticker $orig
        if ($norm) { 
            [void]$tickers.Add($norm) 
            $rawTickerMap[$norm] = $orig
        }
    }
} catch {
    Write-Host "[경고] 거래내역 조회 실패, 기본 목록 사용: $_"
}

Write-Host "총 수집 대상 종목: $($tickers.Count)개 -> $($tickers -join ', ')"

$results = [System.Collections.Generic.List[PSObject]]::new()

foreach ($t in $tickers) {
    $isUs = ($t -match "^[A-Z]{1,5}$")
    if ($isUs) {
        # 미국 ETF/주식 (네이버 글로벌 증권)
        $suffixes = @(".O", ".N", ".K", "")
        $found = $false
        foreach ($s in $suffixes) {
            $url = "https://polling.finance.naver.com/api/realtime/worldstock/stock/$t$s"
            try {
                $resp = Invoke-RestMethod -Uri $url -Headers @{ "User-Agent" = "Mozilla/5.0" } -TimeoutSec 5
                if ($resp.datas -and $resp.datas.Count -gt 0) {
                    $item = $resp.datas[0]
                    $closePrice = [double]($item.closePriceRaw)
                    $changePct = [double]($item.fluctuationsRatioRaw)
                    $changeAmt = [double]($item.compareToPreviousClosePriceRaw)
                    $stockName = if ($item.stockName) { $item.stockName } else { $t }
                    $prevClose = if ($closePrice -gt 0) { $closePrice - $changeAmt } else { $closePrice }

                    $results.Add([PSCustomObject]@{
                        ticker = $t
                        name = $stockName
                        close_price = $closePrice
                        prev_close = $prevClose
                        change_pct = [Math]::Round($changePct, 2)
                        market = "US"
                        updated_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
                    })
                    Write-Host "  [미국] $t ($stockName): `$$closePrice (전일비 $changePct%)"
                    $found = $true
                    break
                }
            } catch {}
        }
        if (-not $found) {
            Write-Host "  [미국 실패] $t 시세 수집 불가"
        }
    } else {
        # 국내 주식/ETF (네이버 국내 증권)
        $norm = Normalize-Ticker $t
        $url = "https://polling.finance.naver.com/api/realtime/domestic/stock/$norm"
        try {
            $resp = Invoke-RestMethod -Uri $url -Headers @{ "User-Agent" = "Mozilla/5.0" } -TimeoutSec 5
            if ($resp.datas -and $resp.datas.Count -gt 0) {
                $item = $resp.datas[0]
                $closePrice = [double]($item.closePriceRaw)
                $changePct = [double]($item.fluctuationsRatioRaw)
                $changeAmt = [double]($item.compareToPreviousClosePriceRaw)
                $stockName = if ($item.stockName) { $item.stockName } else { $norm }
                $prevClose = if ($closePrice -gt 0) { $closePrice - $changeAmt } else { $closePrice }

                $mainObj = [PSCustomObject]@{
                    ticker = $norm
                    name = $stockName
                    close_price = $closePrice
                    prev_close = $prevClose
                    change_pct = [Math]::Round($changePct, 2)
                    market = "KR"
                    updated_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
                }
                $results.Add($mainObj)

                # 만약 사용자가 'O198A0' 처럼 영문 O로 등록했었다면 해당 티커로도 복사 등록하여 100% 매칭 보장
                if ($rawTickerMap.ContainsKey($norm) -and $rawTickerMap[$norm] -ne $norm) {
                    $origKey = $rawTickerMap[$norm]
                    $results.Add([PSCustomObject]@{
                        ticker = $origKey
                        name = $stockName
                        close_price = $closePrice
                        prev_close = $prevClose
                        change_pct = [Math]::Round($changePct, 2)
                        market = "KR"
                        updated_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
                    })
                }

                Write-Host "  [국내] $norm ($stockName): $($closePrice)원 (전일비 $changePct%)"
            } else {
                Write-Host "  [국내 실패] $norm 데이터 없음"
            }
        } catch {
            Write-Host "  [국내 에러] $norm : $_"
        }
    }
}

# Supabase daily_prices 테이블에 Upsert
if ($results.Count -gt 0) {
    $jsonBody = $results | ConvertTo-Json -Depth 3
    $utf8Bytes = [System.Text.Encoding]::UTF8.GetBytes($jsonBody)
    try {
        $upsertUrl = "$SUPABASE_URL/rest/v1/daily_prices"
        $resp = Invoke-RestMethod -Uri $upsertUrl -Method Post -Headers $headers -Body $utf8Bytes
        Write-Host ""
        Write-Host ">>> 네이버 금융 종가 $($results.Count)건 Supabase daily_prices 동기화 완료! <<<"
    } catch {
        Write-Host ">>> Supabase 저장 실패: $_ <<<"
    }
}
