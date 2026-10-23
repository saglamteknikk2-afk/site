<?php
declare(strict_types=1);
define('ST_LIBRARY_MODE', true);
$root = $argv[1] ?? dirname(__DIR__) . '/build/production';
require $root . '/api.php';
$vectors = [
    ['Isisan kombi E01','kombi','Isısan'],
    ['ISISAN klima E01','klima','Isısan'],
    ['E.C.A. klima E01','klima','ECA'],
    ['Vaillant klima E01','klima','Vaillant'],
    ['Daylux kombi E01','kombi','Daylux'],
    ['Daylux klima E01','klima','Daylux'],
    ['Kaira klima E01','klima','Kaira'],
    ['Daxom kombi E01','kombi','Daxom'],
];
foreach ($vectors as [$query, $device, $brand]) {
    $result = st_search(['query' => $query]);
    if ($result['device'] !== $device || $result['brand'] !== $brand || $result['code_definition_verified'] || $result['fault_meaning'] !== '') {
        throw new RuntimeException('Shared registry search scope regression: ' . $query);
    }
}
echo json_encode(['passed' => count($vectors), 'code_tables_changed' => false], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT), "\n";
