param(
    [Parameter(Mandatory = $true)][string]$Timeline,
    [Parameter(Mandatory = $true)][string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
$scenes = Get-Content -LiteralPath $Timeline -Raw | ConvertFrom-Json
$voice = New-Object -ComObject SAPI.SpVoice
try {
    $selected = @($voice.GetVoices() | Where-Object { $_.GetDescription() -like '*Zira*' })
    if ($selected.Count -ne 1) {
        throw 'The video narration requires the Microsoft Zira Desktop English voice.'
    }
    $voice.Voice = $selected[0]
    $voice.Rate = 0
    $voice.Volume = 100
    foreach ($scene in $scenes) {
        $stream = New-Object -ComObject SAPI.SpFileStream
        try {
            $stream.Format.Type = 22
            $stream.Open((Join-Path $OutputDirectory "$($scene.id).wav"), 3, $false)
            $voice.AudioOutputStream = $stream
            [void]$voice.Speak($scene.narration)
        }
        finally {
            $stream.Close()
            [void][Runtime.InteropServices.Marshal]::ReleaseComObject($stream)
        }
    }
}
finally {
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($voice)
}
