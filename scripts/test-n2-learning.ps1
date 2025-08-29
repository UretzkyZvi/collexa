param(
  [string]$AgentId = "agentE2E",
  [string]$BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = 'Stop'

function Invoke-Json {
  param(
    [Parameter(Mandatory=$true)][ValidateSet('GET','POST','PUT','DELETE')][string]$Method,
    [Parameter(Mandatory=$true)][string]$Url,
    [Parameter()][object]$Body
  )
  try {
    if ($PSBoundParameters.ContainsKey('Body') -and $null -ne $Body) {
      $payload = if ($Body -is [string]) { $Body } else { $Body | ConvertTo-Json -Depth 10 }
      return Invoke-RestMethod -Uri $Url -Method $Method -ContentType 'application/json' -Body $payload
    } else {
      return Invoke-RestMethod -Uri $Url -Method $Method
    }
  } catch {
    return [pscustomobject]@{ error = $_.Exception.Message }
  }
}

# Step 1: First iteration (websocket)
$iter1Body = @{ tasks = @('websocket echo test'); docs = @('Frontend guide about React components'); sandbox_mode = 'mock' }
$r1 = Invoke-Json -Method 'POST' -Url ("$BaseUrl/dev/learning/$AgentId/iterate") -Body $iter1Body
$g1 = Invoke-Json -Method 'GET'  -Url ("$BaseUrl/dev/learning/$AgentId/recent")

# Step 2: Second iteration (graphql)
$iter2Body = @{ tasks = @('graphql query introspection'); docs = @(); sandbox_mode = 'mock' }
$r2 = Invoke-Json -Method 'POST' -Url ("$BaseUrl/dev/learning/$AgentId/iterate") -Body $iter2Body
$g2 = Invoke-Json -Method 'GET'  -Url ("$BaseUrl/dev/learning/$AgentId/recent")

# Build summary
$summary = [ordered]@{
  baseUrl = $BaseUrl
  agentId = $AgentId
  post1 = if ($r1.error) { @{ ok = $false; error = $r1.error } } else { @{ ok = ($r1.status -eq 'ok'); iteration = $r1.iteration } }
  get1  = if ($g1.error) { @{ error = $g1.error } } else { @{ iteration = $g1.iteration; tests = $g1.tests } }
  post2 = if ($r2.error) { @{ ok = $false; error = $r2.error } } else { @{ ok = ($r2.status -eq 'ok'); iteration = $r2.iteration } }
  get2  = if ($g2.error) { @{ error = $g2.error } } else { @{ iteration = $g2.iteration; tests = $g2.tests; outcomes = $g2.outcomes } }
}

$json = $summary | ConvertTo-Json -Depth 10
Write-Output $json

# Exit non-zero if any errors
$hasError = $false
foreach ($k in 'post1','get1','post2','get2') { if ($summary[$k].ContainsKey('error')) { $hasError = $true } }
if ($hasError -or -not $summary.post1.ok -or -not $summary.post2.ok) { exit 1 } else { exit 0 }

