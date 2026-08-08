#Requires -Version 5.1
<#
.SYNOPSIS
  Creates/updates the Azure federated identity credential so GitHub Actions
  OIDC login succeeds for this repository.

.DESCRIPTION
  GitHub presents this exact subject (immutable OIDC format):
    repo:sanjanashetti13@192409648/semiconductor-data-plateform@1311673727:ref:refs/heads/main

  Azure must have a Federated credential with that Subject (exact match).

  Prerequisites:
    1. Azure CLI installed (https://aka.ms/installazurecliwindows)
    2. Run: az login
    3. Know the App Registration / managed identity Client ID
       (= GitHub secret AZURE_CLIENT_ID)

.EXAMPLE
  .\scripts\fix_azure_oidc_fic.ps1 -ClientId "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
#>

param(
    [Parameter(Mandatory = $true)]
    [string] $ClientId,

    [string] $CredentialName = "github-main-semiconductor-data-plateform"
)

$ErrorActionPreference = "Stop"

$Issuer = "https://token.actions.githubusercontent.com"
$Audience = "api://AzureADTokenExchange"
$Subject = "repo:sanjanashetti13@192409648/semiconductor-data-plateform@1311673727:ref:refs/heads/main"

Write-Host "Subject to trust:"
Write-Host "  $Subject"
Write-Host ""

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI (az) not found. Install it, run 'az login', then re-run this script."
}

az account show 1>$null 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Not logged in. Run: az login"
}

Write-Host "Looking up app registration for client id $ClientId ..."
$appJson = az ad app show --id $ClientId -o json 2>$null
if ($LASTEXITCODE -ne 0 -or -not $appJson) {
    throw @"
Could not find an App Registration with Application (client) ID: $ClientId

In Azure Portal:
  Microsoft Entra ID → App registrations → search by the AZURE_CLIENT_ID value
  → Certificates & secrets is NOT enough — open Federated credentials
  → Add credential → Other issuer
  → Issuer: $Issuer
  → Subject: $Subject
  → Audience: $Audience
"@
}

$existing = az ad app federated-credential list --id $ClientId -o json | ConvertFrom-Json
$match = $existing | Where-Object { $_.name -eq $CredentialName }

$paramsFile = Join-Path $env:TEMP "fic-params-$CredentialName.json"
@{
    name        = $CredentialName
    issuer      = $Issuer
    subject     = $Subject
    audiences   = @($Audience)
    description = "GitHub Actions main branch OIDC for semiconductor-data-plateform"
} | ConvertTo-Json -Depth 5 | Set-Content -Path $paramsFile -Encoding utf8

if ($match) {
    Write-Host "Updating existing federated credential '$CredentialName' ..."
    az ad app federated-credential update --id $ClientId --federated-credential-id $match.id --parameters "@$paramsFile"
} else {
    Write-Host "Creating federated credential '$CredentialName' ..."
    az ad app federated-credential create --id $ClientId --parameters "@$paramsFile"
}

if ($LASTEXITCODE -ne 0) {
    throw "Failed to create/update federated credential. Check you have Application Administrator (or similar) rights."
}

Write-Host ""
Write-Host "SUCCESS. Wait 1-2 minutes, then re-run the GitHub Action 'Deploy to Azure App Service'."
Write-Host "Trusted subject: $Subject"
