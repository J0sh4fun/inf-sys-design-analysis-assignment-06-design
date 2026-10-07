$ErrorActionPreference = "Stop"
$docxPath = "D:\My workspace\Project\HTTT-assignment06\output\docx\A6_V1_03_NguyenTienDat017.docx"
$renderDir = "D:\My workspace\Project\HTTT-assignment06\tmp\docx-final-render"
$pdfPath = Join-Path $renderDir "A6_final.pdf"
New-Item -ItemType Directory -Path $renderDir -Force | Out-Null
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $document = $word.Documents.Open($docxPath, $false, $false)
    foreach ($toc in $document.TablesOfContents) {
        $toc.Update() | Out-Null
        $toc.Range.Font.Name = "Times New Roman"
        $toc.Range.Font.Size = 8.5
        $toc.Range.ParagraphFormat.SpaceBefore = 0
        $toc.Range.ParagraphFormat.SpaceAfter = 0
        $toc.Range.ParagraphFormat.LineSpacingRule = 0
    }
    foreach ($field in $document.Fields) { $field.Update() | Out-Null }
    $document.Repaginate()
    $document.Save()
    $document.ExportAsFixedFormat($pdfPath, 17)
    $document.Close($false)
}
finally {
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
}
Write-Output $pdfPath
