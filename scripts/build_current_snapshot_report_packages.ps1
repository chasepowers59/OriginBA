Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = 'C:\Users\cvpow\OneDrive\Desktop\OriginBA'
$exportRoot = Join-Path $repoRoot 'tmp\snapshot_folder_zip_inspect'
$resourcesRoot = Join-Path $exportRoot 'resources'
$outputRoot = Join-Path $repoRoot 'domains\exports\manual_imports\current_snapshot_report_packages'
$workRoot = Join-Path $repoRoot 'tmp\current_snapshot_report_packages_work'

Add-Type -AssemblyName System.IO.Compression.FileSystem

function Reset-Directory {
    param([string]$Path)
    if (Test-Path $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
    New-Item -ItemType Directory -Path $Path | Out-Null
}

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Get-ParentUri {
    param([string]$Uri)
    $normalized = $Uri.TrimEnd('/')
    $lastSlash = $normalized.LastIndexOf('/')
    if ($lastSlash -lt 0) {
        throw "Cannot determine parent URI for $Uri"
    }
    return $normalized.Substring(0, $lastSlash)
}

function Convert-UriToResourcePath {
    param(
        [string]$Uri,
        [string]$Suffix = ''
    )
    $relative = $Uri.TrimStart('/').Replace('/', '\') + $Suffix
    return Join-Path $resourcesRoot $relative
}

function Convert-UriToPackagePath {
    param(
        [string]$PackageResourcesRoot,
        [string]$Uri,
        [string]$Suffix = ''
    )
    $relative = $Uri.TrimStart('/').Replace('/', '\') + $Suffix
    return Join-Path $PackageResourcesRoot $relative
}

function Ensure-FolderChain {
    param(
        [string]$PackageResourcesRoot,
        [string]$FolderUri
    )

    $parts = $FolderUri.Trim('/').Split('/')
    $current = ''
    foreach ($part in $parts) {
        $current = if ([string]::IsNullOrEmpty($current)) { $part } else { "$current/$part" }
        $targetDir = Join-Path $PackageResourcesRoot ($current.Replace('/', '\'))
        Ensure-Directory -Path $targetDir

        $sourceFolderXml = Join-Path $resourcesRoot ($current.Replace('/', '\') + '\.folder.xml')
        if (Test-Path $sourceFolderXml) {
            Copy-Item -LiteralPath $sourceFolderXml -Destination (Join-Path $targetDir '.folder.xml') -Force
        }
    }
}

function Copy-DomainBundle {
    param(
        [string]$PackageResourcesRoot,
        [string]$DomainUri
    )

    $domainFolderUri = Get-ParentUri -Uri $DomainUri
    Ensure-FolderChain -PackageResourcesRoot $PackageResourcesRoot -FolderUri $domainFolderUri

    $sourceDomainXml = Convert-UriToResourcePath -Uri $DomainUri -Suffix '.xml'
    $targetDomainXml = Convert-UriToPackagePath -PackageResourcesRoot $PackageResourcesRoot -Uri $DomainUri -Suffix '.xml'
    Copy-Item -LiteralPath $sourceDomainXml -Destination $targetDomainXml -Force

    $sourceSchemaPath = Convert-UriToResourcePath -Uri $DomainUri -Suffix '_files\schema.data'
    if (Test-Path $sourceSchemaPath) {
        $targetSchemaPath = Convert-UriToPackagePath -PackageResourcesRoot $PackageResourcesRoot -Uri $DomainUri -Suffix '_files\schema.data'
        Ensure-Directory -Path (Split-Path -Parent $targetSchemaPath)
        Copy-Item -LiteralPath $sourceSchemaPath -Destination $targetSchemaPath -Force
    }
}

function Write-IndexXml {
    param(
        [string]$DestinationPath,
        [string]$ResourceUri
    )

    $xml = @"
<?xml version="1.0" encoding="UTF-8"?>
<export><property name="keyalias" value="d9afddff-1ad9-4d9c-b6a2-dba56f2f1d9f"/><module id="repositoryResources"><resource>$ResourceUri</resource></module><module id="favorites"/><property name="pathProcessorId" value="zip"/><property name="rootTenantId" value="organizations"/><property name="jsVersion" value="8.1.0 PRO"/><property name="encrypted" value="4A5253495600000010E39ED59D4D11651BE76D778DFFE5B768C2164404A5A4D9FF03E1DEEB8CC4CC96"/></export>
"@
    Set-Content -LiteralPath $DestinationPath -Value $xml -Encoding UTF8
}

function Set-AdhocXmlValues {
    param(
        [string]$XmlPath,
        [string]$SourceFolderUri,
        [string]$SourceResourceUri,
        [string]$TargetFolderUri,
        [string]$TargetResourceUri,
        [string]$NewName,
        [string]$NewLabel,
        [string]$NewDescription
    )

    $raw = Get-Content -LiteralPath $XmlPath -Raw
    $raw = $raw.Replace($SourceResourceUri + '_files', $TargetResourceUri + '_files')
    $raw = $raw.Replace($SourceFolderUri, $TargetFolderUri)
    [xml]$doc = $raw
    $root = $doc.adhocDataView
    if ($null -eq $root) {
        throw "Unexpected Ad Hoc XML structure in $XmlPath"
    }

    $setNode = {
        param($parent, [string]$nodeName, [string]$value)
        $node = $parent.SelectSingleNode($nodeName)
        if ($null -eq $node) {
            $node = $doc.CreateElement($nodeName)
            [void]$parent.AppendChild($node)
        }
        $node.InnerText = $value
    }

    $timestamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.000Z')
    & $setNode $root 'folder' $TargetFolderUri
    & $setNode $root 'name' $NewName
    & $setNode $root 'label' $NewLabel
    & $setNode $root 'description' $NewDescription
    & $setNode $root 'creationDate' $timestamp
    & $setNode $root 'updateDate' $timestamp

    $settings = New-Object System.Xml.XmlWriterSettings
    $settings.Indent = $true
    $settings.OmitXmlDeclaration = $false
    $settings.Encoding = [System.Text.UTF8Encoding]::new($false)
    $writer = [System.Xml.XmlWriter]::Create($XmlPath, $settings)
    $doc.Save($writer)
    $writer.Dispose()
}

function Set-StateTitle {
    param(
        [string]$StateXmlPath,
        [string]$Title
    )

    if (-not (Test-Path $StateXmlPath)) {
        return
    }

    $raw = Get-Content -LiteralPath $StateXmlPath -Raw
    $updated = [regex]::Replace($raw, '<title>.*?</title>', "<title>$Title</title>", 'Singleline')
    Set-Content -LiteralPath $StateXmlPath -Value $updated -Encoding UTF8
}

function Zip-PackageDirectory {
    param(
        [string]$SourceDirectory,
        [string]$ZipPath
    )

    if (Test-Path $ZipPath) {
        Remove-Item -LiteralPath $ZipPath -Force
    }
    [System.IO.Compression.ZipFile]::CreateFromDirectory($SourceDirectory, $ZipPath, [System.IO.Compression.CompressionLevel]::Optimal, $false)
}

function Convert-ControlToXml {
    param(
        [hashtable]$Control,
        [string]$ControlFolderUri,
        [string]$Timestamp
    )

    $id = $Control.id
    $label = $Control.label
    $mandatory = if ($Control.mandatory) { 'true' } else { 'false' }
    $visible = if ($Control.visible) { 'true' } else { 'false' }

    switch ($Control.type) {
        'singleValueDateTime' {
            return @"
    <inputControl>
        <localResource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" exportedWithPermissions="false" xsi:type="inputControl">
            <folder>$ControlFolderUri</folder>
            <name>$id</name>
            <version>1</version>
            <label>$label</label>
            <creationDate>$Timestamp</creationDate>
            <updateDate>$Timestamp</updateDate>
            <type>2</type>
            <mandatory>$mandatory</mandatory>
            <readOnly>false</readOnly>
            <visible>$visible</visible>
            <dataType>
                <localResource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" exportedWithPermissions="false" xsi:type="dataType">
                    <folder>$ControlFolderUri/${id}_files</folder>
                    <name>dt_$id</name>
                    <version>1</version>
                    <label>dt_$id</label>
                    <creationDate>$Timestamp</creationDate>
                    <updateDate>$Timestamp</updateDate>
                    <type>4</type>
                    <strictMin>false</strictMin>
                    <strictMax>false</strictMax>
                </localResource>
            </dataType>
        </localResource>
    </inputControl>
"@
        }
        'singleValueNumber' {
            return @"
    <inputControl>
        <localResource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" exportedWithPermissions="false" xsi:type="inputControl">
            <folder>$ControlFolderUri</folder>
            <name>$id</name>
            <version>1</version>
            <label>$label</label>
            <creationDate>$Timestamp</creationDate>
            <updateDate>$Timestamp</updateDate>
            <type>2</type>
            <mandatory>$mandatory</mandatory>
            <readOnly>false</readOnly>
            <visible>$visible</visible>
            <dataType>
                <localResource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" exportedWithPermissions="false" xsi:type="dataType">
                    <folder>$ControlFolderUri/${id}_files</folder>
                    <name>dt_$id</name>
                    <version>1</version>
                    <label>dt_$id</label>
                    <creationDate>$Timestamp</creationDate>
                    <updateDate>$Timestamp</updateDate>
                    <type>2</type>
                    <strictMin>false</strictMin>
                    <strictMax>false</strictMax>
                </localResource>
            </dataType>
        </localResource>
    </inputControl>
"@
        }
        'singleValueText' {
            return @"
    <inputControl>
        <localResource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" exportedWithPermissions="false" xsi:type="inputControl">
            <folder>$ControlFolderUri</folder>
            <name>$id</name>
            <version>1</version>
            <label>$label</label>
            <creationDate>$Timestamp</creationDate>
            <updateDate>$Timestamp</updateDate>
            <type>2</type>
            <mandatory>$mandatory</mandatory>
            <readOnly>false</readOnly>
            <visible>$visible</visible>
            <dataType>
                <localResource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" exportedWithPermissions="false" xsi:type="dataType">
                    <folder>$ControlFolderUri/${id}_files</folder>
                    <name>dt_$id</name>
                    <version>1</version>
                    <label>dt_$id</label>
                    <creationDate>$Timestamp</creationDate>
                    <updateDate>$Timestamp</updateDate>
                    <type>1</type>
                </localResource>
            </dataType>
        </localResource>
    </inputControl>
"@
        }
        'singleValueBoolean' {
            return @"
    <inputControl>
        <localResource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" exportedWithPermissions="false" xsi:type="inputControl">
            <folder>$ControlFolderUri</folder>
            <name>$id</name>
            <version>1</version>
            <label>$label</label>
            <creationDate>$Timestamp</creationDate>
            <updateDate>$Timestamp</updateDate>
            <type>1</type>
            <mandatory>$mandatory</mandatory>
            <readOnly>false</readOnly>
            <visible>$visible</visible>
        </localResource>
    </inputControl>
"@
        }
        default {
            throw "Unsupported input control type: $($Control.type)"
        }
    }
}

function New-ReportUnitXml {
    param(
        [string]$FolderUri,
        [string]$Name,
        [string]$Label,
        [string]$Description,
        [string]$DomainUri,
        [array]$Controls
    )

    $timestamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.000Z')
    $controlFolderUri = "$FolderUri/${Name}_files"
    $controlsXml = ($Controls | ForEach-Object { Convert-ControlToXml -Control $_ -ControlFolderUri $controlFolderUri -Timestamp $timestamp }) -join ''

    return @"
<?xml version="1.0" encoding="UTF-8"?>
<reportUnit exportedWithPermissions="true">
    <folder>$FolderUri</folder>
    <name>$Name</name>
    <version>1</version>
    <label>$Label</label>
    <description>$Description</description>
    <creationDate>$timestamp</creationDate>
    <updateDate>$timestamp</updateDate>
    <mainReport>
        <localResource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" exportedWithPermissions="false" dataFile="main_jrxml.data" xsi:type="fileResource">
            <folder>$controlFolderUri</folder>
            <name>main_jrxml</name>
            <version>1</version>
            <label>Main jrxml</label>
            <creationDate>$timestamp</creationDate>
            <updateDate>$timestamp</updateDate>
            <fileType>jrxml</fileType>
        </localResource>
    </mainReport>
    <dataSource>
        <uri>$DomainUri</uri>
    </dataSource>
$controlsXml    <inputControlRenderingView></inputControlRenderingView>
    <reportRenderingView></reportRenderingView>
    <alwaysPromptControls>true</alwaysPromptControls>
    <controlsLayout>1</controlsLayout>
</reportUnit>
"@
}

function New-AdhocPackage {
    param([hashtable]$Spec)

    $packageName = $Spec.Name
    $packageDir = Join-Path $workRoot $packageName
    $packageResourcesRoot = Join-Path $packageDir 'resources'
    Reset-Directory -Path $packageDir
    Ensure-Directory -Path $packageResourcesRoot

    Ensure-FolderChain -PackageResourcesRoot $packageResourcesRoot -FolderUri $Spec.TargetFolderUri
    Copy-DomainBundle -PackageResourcesRoot $packageResourcesRoot -DomainUri $Spec.DomainUri

    $sourceUri = $Spec.SourceUri
    $sourceFolderUri = Get-ParentUri -Uri $sourceUri
    $sourceXmlPath = Convert-UriToResourcePath -Uri $sourceUri -Suffix '.xml'
    $sourceFilesPath = Convert-UriToResourcePath -Uri $sourceUri -Suffix '_files'
    $targetUri = "$($Spec.TargetFolderUri)/$($Spec.Name)"
    $targetXmlPath = Convert-UriToPackagePath -PackageResourcesRoot $packageResourcesRoot -Uri $targetUri -Suffix '.xml'
    $targetFilesPath = Convert-UriToPackagePath -PackageResourcesRoot $packageResourcesRoot -Uri $targetUri -Suffix '_files'

    Ensure-Directory -Path (Split-Path -Parent $targetXmlPath)
    Copy-Item -LiteralPath $sourceXmlPath -Destination $targetXmlPath -Force
    Copy-Item -LiteralPath $sourceFilesPath -Destination $targetFilesPath -Recurse -Force

    Set-AdhocXmlValues -XmlPath $targetXmlPath -SourceFolderUri $sourceFolderUri -SourceResourceUri $sourceUri -TargetFolderUri $Spec.TargetFolderUri -TargetResourceUri $targetUri -NewName $Spec.Name -NewLabel $Spec.Label -NewDescription $Spec.Description
    Set-StateTitle -StateXmlPath (Join-Path $targetFilesPath 'stateXML.data') -Title $Spec.StateTitle

    Write-IndexXml -DestinationPath (Join-Path $packageDir 'index.xml') -ResourceUri $targetUri
    $zipPath = Join-Path $outputRoot ($packageName + '.zip')
    Zip-PackageDirectory -SourceDirectory $packageDir -ZipPath $zipPath

    return [pscustomobject]@{
        Package = $packageName
        Type = 'Ad Hoc'
        TargetUri = $targetUri
        DomainUri = $Spec.DomainUri
        ZipPath = $zipPath
        SourceArtifact = $sourceUri
    }
}

function New-ReportUnitPackage {
    param([hashtable]$Spec)

    $packageName = $Spec.Name
    $packageDir = Join-Path $workRoot $packageName
    $packageResourcesRoot = Join-Path $packageDir 'resources'
    Reset-Directory -Path $packageDir
    Ensure-Directory -Path $packageResourcesRoot

    Ensure-FolderChain -PackageResourcesRoot $packageResourcesRoot -FolderUri $Spec.TargetFolderUri
    Copy-DomainBundle -PackageResourcesRoot $packageResourcesRoot -DomainUri $Spec.DomainUri

    $targetUri = "$($Spec.TargetFolderUri)/$($Spec.Name)"
    $targetXmlPath = Convert-UriToPackagePath -PackageResourcesRoot $packageResourcesRoot -Uri $targetUri -Suffix '.xml'
    $targetFilesPath = Convert-UriToPackagePath -PackageResourcesRoot $packageResourcesRoot -Uri $targetUri -Suffix '_files'
    Ensure-Directory -Path $targetFilesPath

    $controlJson = Get-Content -LiteralPath $Spec.InputControlJson -Raw | ConvertFrom-Json
    $controls = @($controlJson.inputControls | ForEach-Object { @{ id = $_.id; label = $_.label; type = $_.type; mandatory = [bool]$_.mandatory; visible = [bool]$_.visible } })

    $reportUnitXml = New-ReportUnitXml -FolderUri $Spec.TargetFolderUri -Name $Spec.Name -Label $Spec.Label -Description $Spec.Description -DomainUri $Spec.DomainUri -Controls $controls
    Set-Content -LiteralPath $targetXmlPath -Value $reportUnitXml -Encoding UTF8
    Copy-Item -LiteralPath $Spec.SourceJrxml -Destination (Join-Path $targetFilesPath 'main_jrxml.data') -Force

    if (Test-Path $Spec.StateXmlTemplate) {
        Copy-Item -LiteralPath $Spec.StateXmlTemplate -Destination (Join-Path $targetFilesPath 'stateXML.data') -Force
    }

    Write-IndexXml -DestinationPath (Join-Path $packageDir 'index.xml') -ResourceUri $targetUri
    $zipPath = Join-Path $outputRoot ($packageName + '.zip')
    Zip-PackageDirectory -SourceDirectory $packageDir -ZipPath $zipPath

    return [pscustomobject]@{
        Package = $packageName
        Type = 'Report Unit'
        TargetUri = $targetUri
        DomainUri = $Spec.DomainUri
        ZipPath = $zipPath
        SourceArtifact = $Spec.SourceJrxml
    }
}

Reset-Directory -Path $outputRoot
Reset-Directory -Path $workRoot

$paymentsDomain = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Cashiering/Payments/Tender___Payments_Snapshot___Domain'
$glDomain = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Financial_Transaction/General_Ledger/FT_and_GL_Snapshot___Domain'
$ftDomain = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Financial_Transaction/Financial_Transaction/Financial_Transaction_Snapshot___Domain'
$usageDomain = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Meter_Operations/Usage_Transactions/Usage_Transactions_Snapshot___Domain'
$measurementDomain = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Meter_Operations/Measurements/Measurement_Snapshot___Domain'
$billedAmountDomain = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Billed_Usage/Amount_Billed/Billed_Usage_Snapshot___Domain'
$billedDeterminantDomain = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Billed_Usage/Billed_Usage/Billed_Usage_SQ_Snapshot___Domain'

$adhocSpecs = @(
    @{
        Name = 'Payments___Payment_Channel_Summary'
        Label = 'Payments - Payment Channel Summary'
        Description = 'Chart | Payment amounts by source family and tender source'
        StateTitle = 'Payment Channel Summary'
        SourceUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Cashiering/Payments/Payments___Tender_Source'
        TargetFolderUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Cashiering/Payments'
        DomainUri = $paymentsDomain
    },
    @{
        Name = 'Payments___Tender_Control_Balancing'
        Label = 'Payments - Tender Control Balancing'
        Description = 'Table | Tender control balancing details by control, source, and amount'
        StateTitle = 'Tender Control Balancing'
        SourceUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Cashiering/Tender_Control/Tender_Controls___Balancing_Details'
        TargetFolderUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Cashiering/Payments'
        DomainUri = $paymentsDomain
    },
    @{
        Name = 'General_Ledger___Distribution_Code_Summary'
        Label = 'General Ledger - Distribution Code Summary'
        Description = 'Table | Governed GL account and distribution code summary'
        StateTitle = 'GL Distribution Code Summary'
        SourceUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Financial_Transaction/General_Ledger/General_Ledger___GL_Account_and_Distribution'
        TargetFolderUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Financial_Transaction/General_Ledger'
        DomainUri = $glDomain
    },
    @{
        Name = 'Usage_Transactions___Operations_Summary'
        Label = 'Usage Transactions - Operations Summary'
        Description = 'Chart | Usage transaction counts across service agreement type'
        StateTitle = 'Usage Operations Summary'
        SourceUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Meter_Operations/Usage_Transactions/Usage_Transaction___By_SA_Type'
        TargetFolderUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Meter_Operations/Usage_Transactions'
        DomainUri = $usageDomain
    },
    @{
        Name = 'Measurement___Quality_Monitor'
        Label = 'Measurements - Quality Monitor'
        Description = 'Table | Measuring component health and measurement quality signals'
        StateTitle = 'Measurement Quality Monitor'
        SourceUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Meter_Operations/Measurements/Measurement___Measuring_Component_Health'
        TargetFolderUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Meter_Operations/Measurements'
        DomainUri = $measurementDomain
    },
    @{
        Name = 'Billed_Usage___Summary'
        Label = 'Billed Usage - Summary'
        Description = 'Chart | Total billed amount by utility service type'
        StateTitle = 'Billed Usage Summary'
        SourceUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Billed_Usage/Amount_Billed/Billed_Usage___By_Service_Type'
        TargetFolderUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Billed_Usage/Amount_Billed'
        DomainUri = $billedAmountDomain
    },
    @{
        Name = 'Billed_Usage___Determinant_Analysis'
        Label = 'Billed Usage - Determinant Analysis'
        Description = 'Table | Billed determinant analysis across UOM, TOU, and SQI'
        StateTitle = 'Billed Determinant Analysis'
        SourceUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Billed_Usage/Billed_Usage/Billed_Usage___Segment_Determinant'
        TargetFolderUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Billed_Usage/Billed_Usage'
        DomainUri = $billedDeterminantDomain
    },
    @{
        Name = 'Financial_Transactions___Operations_Report'
        Label = 'Financial Transactions - Operations Report'
        Description = 'Table | FT header operations summary across service agreement type and FT type'
        StateTitle = 'Financial Transaction Operations Report'
        SourceUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Financial_Transaction/Financial_Transaction/Financial_Transactions___Service_Type_FT_Summary'
        TargetFolderUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Financial_Transaction/Financial_Transaction'
        DomainUri = $ftDomain
    }
)

$genericStateTemplate = Join-Path $repoRoot 'tmp\gl_report_fixed\resources\organizations\organization_1\organizations\Origin_DEV\SmartCity\Report\Workstreams\Development\Snapshots\Financial_Transaction\General_Ledger\General_Ledger___Batch_Number_Report_files\stateXML.data'

$reportSpecs = @(
    @{
        Name = 'Payments___Deposit_Control_Reconciliation_Report'
        Label = 'Payments - Deposit Control Reconciliation Report'
        Description = 'Controlled reconciliation report for deposit controls, tender totals, and variances.'
        TargetFolderUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Cashiering/Payments'
        DomainUri = $paymentsDomain
        SourceJrxml = Join-Path $repoRoot 'reports\deposit_control_reconciliation_report.jrxml'
        InputControlJson = Join-Path $repoRoot 'server\input_controls\deposit_control_reconciliation_report_input_controls.json'
        StateXmlTemplate = $genericStateTemplate
    },
    @{
        Name = 'General_Ledger___Exception_Monitor_Report'
        Label = 'General Ledger - Exception Monitor Report'
        Description = 'Batch-focused control report for unusual GL rows and exception flags.'
        TargetFolderUri = '/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Development/Snapshots/Financial_Transaction/General_Ledger'
        DomainUri = $glDomain
        SourceJrxml = Join-Path $repoRoot 'reports\general_ledger_exception_monitor.jrxml'
        InputControlJson = Join-Path $repoRoot 'server\input_controls\general_ledger_exception_monitor_input_controls.json'
        StateXmlTemplate = $genericStateTemplate
    }
)

$manifest = @()
$manifest += $adhocSpecs | ForEach-Object { New-AdhocPackage -Spec $_ }
$manifest += $reportSpecs | ForEach-Object { New-ReportUnitPackage -Spec $_ }

foreach ($jrxmlPath in @(
    (Join-Path $repoRoot 'reports\deposit_control_reconciliation_report.jrxml'),
    (Join-Path $repoRoot 'reports\general_ledger_exception_monitor.jrxml')
)) {
    [xml](Get-Content -LiteralPath $jrxmlPath -Raw) | Out-Null
}

foreach ($jsonPath in @(
    (Join-Path $repoRoot 'server\input_controls\deposit_control_reconciliation_report_input_controls.json'),
    (Join-Path $repoRoot 'server\input_controls\deposit_control_reconciliation_report_input_controls_rest.json'),
    (Join-Path $repoRoot 'server\input_controls\general_ledger_exception_monitor_input_controls.json'),
    (Join-Path $repoRoot 'server\input_controls\general_ledger_exception_monitor_input_controls_rest.json')
)) {
    Get-Content -LiteralPath $jsonPath -Raw | ConvertFrom-Json | Out-Null
}

foreach ($item in $manifest) {
    $zipFile = $item.ZipPath
    if (-not (Test-Path $zipFile)) {
        throw "Expected package zip not found: $zipFile"
    }
}

$manifestJsonPath = Join-Path $outputRoot 'manifest.json'
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestJsonPath -Encoding UTF8

$manifestMdPath = Join-Path $outputRoot 'README.md'
$lines = @(
    '# Current Snapshot Report Packages',
    '',
    'Import-ready packages built from the exported snapshot repository structure.',
    '',
    '| Package | Type | Target URI | Domain URI | Source Artifact |',
    '| --- | --- | --- | --- | --- |'
)
foreach ($item in $manifest) {
    $lines += "| $($item.Package) | $($item.Type) | ``$($item.TargetUri)`` | ``$($item.DomainUri)`` | ``$($item.SourceArtifact)`` |"
}
$lines | Set-Content -LiteralPath $manifestMdPath -Encoding UTF8

Write-Host "Built $($manifest.Count) import packages in $outputRoot"
