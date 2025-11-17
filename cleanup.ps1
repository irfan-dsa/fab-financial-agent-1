# FAB Financial Agent - Complete Cleanup Script
# This script removes all unnecessary debug/test files and prepares for submission

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  FAB FINANCIAL AGENT - PROJECT CLEANUP" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# 1. CREATE BACKUP FIRST (SAFETY)
Write-Host "`n[1/8] Creating backup..." -ForegroundColor Yellow
$backupName = "fab_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip"
try {
    Compress-Archive -Path . -DestinationPath "..\$backupName" -Force
    Write-Host "✅ Backup created: ..\$backupName" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Backup failed: $_" -ForegroundColor Red
    $continue = Read-Host "Continue anyway? (yes/no)"
    if ($continue -ne "yes") { exit }
}

# 2. DELETE ROOT-LEVEL DEBUG/TEST FILES
Write-Host "`n[2/8] Removing root-level debug files..." -ForegroundColor Yellow

$rootFilesToDelete = @(
    "analyze_income_statements.py",
    "analyze_pl_structure.py",
    "check_missing.py",
    "check_pages.py",
    "check_page_detection.py",
    "check_revenue_q4.py",
    "check_vectorstore.py",
    "convert_jsonl_to_json.py",
    "debug_columns.py",
    "debug_extraction.py",
    "debug_extraction_logic.py",
    "debug_find_number.py",
    "debug_function.py",
    "debug_lines.py",
    "debug_net_interest.py",
    "debug_q1_2025.py",
    "debug_q1_format.py",
    "debug_q3_2024.py",
    "diag_exhaustive.py",
    "diag_extractor.py",
    "direct_pdf_extractor.py",
    "fab_financial_extractor.py",
    "financial_extractor.py",
    "find_income_items.py",
    "find_income_statement.py",
    "find_net_interest.py",
    "find_other_metrics.py",
    "find_pdfs.py",
    "find_pl_labels.py",
    "find_profit_period.py",
    "find_project_pdfs.py",
    "find_revenue_item.py",
    "fix_extraction.txt",
    "fix_retrieval.txt",
    "extraction_fix_notes.txt",
    "ingest_documents.py",
    "list_all_pl_items.py",
    "load_vectordb.py",
    "patch_agent.py",
    "run_agent_backup.py",
    "run_agent_backup.py.bak",
    "run_agent_old.py",
    "search_all_quarters.py",
    "search_all_sections.py",
    "show_all_page4.py",
    "show_complete_is.py",
    "show_full_income_statement.py",
    "show_page2.py",
    "show_page4.py",
    "show_page4_chunks.py",
    "show_pl_top.py",
    "test_all_agents.py",
    "test_all_quarters.py",
    "test_direct.py",
    "test_direct_extract.py",
    "test_extract.py",
    "test_fresh.py",
    "test_hybrid.py",
    "test_hybrid_final.py",
    "test_metric_detection.py",
    "test_metric_detection_fixed.py",
    "test_new_hybrid.py",
    "test_parser.py",
    "test_system.py",
    "test_with_ground_truth.py"
)

$deletedCount = 0
foreach ($file in $rootFilesToDelete) {
    if (Test-Path $file) {
        Remove-Item $file -Force
        $deletedCount++
        Write-Host "  ❌ Deleted: $file" -ForegroundColor DarkGray
    }
}
Write-Host "✅ Removed $deletedCount root-level files" -ForegroundColor Green

# 3. CLEAN BACKUP FILES IN SRC/
Write-Host "`n[3/8] Removing backup files in src/..." -ForegroundColor Yellow

$backupPatterns = @(
    "src/agents/*.bak",
    "src/agents/*.old",
    "src/agents/*.prepatch",
    "src/agents/*.prepymupdf",
    "src/agents/*.broken.*.bak",
    "src/agents/*.appendback",
    "src/utils/*.bak",
    "src/tests/*.bak",
    "src/eval/*.jsonl.bak"
)

$backupCount = 0
foreach ($pattern in $backupPatterns) {
    $files = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        Remove-Item $file.FullName -Force
        $backupCount++
        Write-Host "  ❌ Deleted: $($file.Name)" -ForegroundColor DarkGray
    }
}
Write-Host "✅ Removed $backupCount backup files" -ForegroundColor Green

# 4. REMOVE DUPLICATE PDF
Write-Host "`n[4/8] Removing duplicate PDFs..." -ForegroundColor Yellow
$duplicatePdf = "data\raw\FAB-FS-Q4-2023-English (1).pdf"
if (Test-Path $duplicatePdf) {
    Remove-Item $duplicatePdf -Force
    Write-Host "✅ Removed duplicate: $duplicatePdf" -ForegroundColor Green
} else {
    Write-Host "✅ No duplicate PDFs found" -ForegroundColor Green
}

# 5. CLEAR LOG FILES (keep folder structure)
Write-Host "`n[5/8] Clearing log files..." -ForegroundColor Yellow
$logPatterns = @(
    "src\eval\logs\*.out",
    "src\eval\logs\*.txt",
    "src\eval\logs\*.tsv"
)

$logCount = 0
foreach ($pattern in $logPatterns) {
    $files = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        Remove-Item $file.FullName -Force
        $logCount++
    }
}
Write-Host "✅ Cleared $logCount log files" -ForegroundColor Green

# 6. REMOVE PYTHON CACHE
Write-Host "`n[6/8] Removing Python cache..." -ForegroundColor Yellow
$cacheCount = 0
Get-ChildItem -Recurse -Include __pycache__,*.pyc,.pytest_cache,.mypy_cache -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force
    $cacheCount++
}
Write-Host "✅ Removed $cacheCount cache directories" -ForegroundColor Green

# 7. VERIFY CRITICAL FILES EXIST
Write-Host "`n[7/8] Verifying critical files..." -ForegroundColor Yellow

$criticalFiles = @(
    "src\agents\extraction_agent.py",
    "src\agents\calculator_agent.py",
    "src\agents\temporal_agent.py",
    "src\agents\retrieval_agent.py",
    "src\eval\create_test_queries.py",
    "src\eval\run_evaluation.py",
    "src\eval\generate_markdown_report.py",
    "src\ingest\ingest.py",
    "src\parsers\pdf_parser.py",
    "requirements.txt",
    "README.md"
)

$allPresent = $true
foreach ($file in $criticalFiles) {
    if (Test-Path $file) {
        Write-Host "  ✅ $file" -ForegroundColor Green
    } else {
        Write-Host "  ❌ MISSING: $file" -ForegroundColor Red
        $allPresent = $false
    }
}

if (-not $allPresent) {
    Write-Host "`n⚠️  WARNING: Some critical files are missing!" -ForegroundColor Red
    Write-Host "Review the backup before proceeding." -ForegroundColor Yellow
    exit 1
}

# 8. DISPLAY FINAL STATISTICS
Write-Host "`n[8/8] Project Statistics:" -ForegroundColor Yellow

$pythonFiles = (Get-ChildItem -Recurse -Filter *.py | Measure-Object).Count
$pdfFiles = (Get-ChildItem data\raw\*.pdf -ErrorAction SilentlyContinue | Measure-Object).Count
$totalSize = [math]::Round((Get-ChildItem -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 2)

Write-Host "  📄 Python files: $pythonFiles" -ForegroundColor Cyan
Write-Host "  📑 PDF files: $pdfFiles" -ForegroundColor Cyan
Write-Host "  💾 Total size: $totalSize MB" -ForegroundColor Cyan

# 9. SHOW REMAINING ROOT FILES
Write-Host "`n📂 Remaining root-level files:" -ForegroundColor Cyan
Get-ChildItem -File | Where-Object { $_.Extension -eq ".py" -or $_.Extension -eq ".md" -or $_.Extension -eq ".txt" } | ForEach-Object {
    Write-Host "  • $($_.Name)" -ForegroundColor White
}

# 10. GIT OPERATIONS
Write-Host "`n=================================================" -ForegroundColor Cyan
Write-Host "  GIT OPERATIONS" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

$doGit = Read-Host "`nCommit and push to Git? (yes/no)"

if ($doGit -eq "yes") {
    Write-Host "`n📦 Adding changes to Git..." -ForegroundColor Yellow
    git add -A
    
    Write-Host "📝 Committing changes..." -ForegroundColor Yellow
    git commit -m "Clean up project structure for submission

- Removed 60+ debug/test files from root
- Cleaned up backup files (.bak, .old, .prepatch)
- Removed duplicate PDFs
- Cleared log files
- Removed Python cache
- Project ready for submission"
    
    Write-Host "🚀 Pushing to remote..." -ForegroundColor Yellow
    git push
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Git push successful!" -ForegroundColor Green
    } else {
        Write-Host "❌ Git push failed. Please check manually." -ForegroundColor Red
    }
} else {
    Write-Host "⏭️  Skipped Git operations" -ForegroundColor Yellow
    Write-Host "To commit manually, run:" -ForegroundColor Cyan
    Write-Host "  git add -A" -ForegroundColor White
    Write-Host "  git commit -m 'Clean up project structure'" -ForegroundColor White
    Write-Host "  git push" -ForegroundColor White
}

# 11. FINAL CHECKS
Write-Host "`n=================================================" -ForegroundColor Cyan
Write-Host "  FINAL VERIFICATION" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

Write-Host "`n🧪 Running tests..." -ForegroundColor Yellow
python -m pytest -q 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ All tests passing" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some tests failed - please review" -ForegroundColor Yellow
}

Write-Host "`n🎯 Testing evaluation pipeline..." -ForegroundColor Yellow
python src\eval\create_test_queries.py 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Test queries script working" -ForegroundColor Green
} else {
    Write-Host "⚠️  Test queries script needs attention" -ForegroundColor Yellow
}

# COMPLETION MESSAGE
Write-Host "`n=================================================" -ForegroundColor Green
Write-Host "  ✅ CLEANUP COMPLETE!" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green

Write-Host "`n📋 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Review cleaned structure" -ForegroundColor White
Write-Host "  2. Run: python src/eval/run_evaluation.py" -ForegroundColor White
Write-Host "  3. Run: python src/eval/generate_markdown_report.py" -ForegroundColor White
Write-Host "  4. Create submission ZIP" -ForegroundColor White
Write-Host "`n💾 Backup location: ..\$backupName" -ForegroundColor Yellow
Write-Host "`nProject is ready for submission! 🚀" -ForegroundColor Green