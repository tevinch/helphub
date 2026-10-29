<?php

declare(strict_types=1);

use App\Dto\AvailabilityStrategyDto;
use App\Enums\StockStatus;
use App\Services\StrategyExtractor;
use Jez500\WebScraperForLaravel\WebScraperHttp;

$installation = $argv[1] ?? '';
$autoload = rtrim($installation, DIRECTORY_SEPARATOR).'/vendor/autoload.php';
if ($installation === '' || !is_file($autoload)) {
    fwrite(STDERR, "Usage: php verify.php /path/to/installed/pricebuddy\n");
    exit(2);
}
require $autoload;

function checkSame(mixed $actual, mixed $expected, string $message): void
{
    if ($actual !== $expected) {
        throw new RuntimeException($message.'; expected '.json_encode($expected).', got '.json_encode($actual));
    }
}

$config = json_decode(file_get_contents(__DIR__.'/availability.json'), true, flags: JSON_THROW_ON_ERROR);
$fixtures = json_decode(file_get_contents(__DIR__.'/fixtures.json'), true, flags: JSON_THROW_ON_ERROR);
$strategy = AvailabilityStrategyDto::fromArray($config);
if ($strategy === null) {
    throw new RuntimeException('Native availability strategy was not created.');
}

foreach ($fixtures as $fixture) {
    // setBody() supplies already-fetched HTML to the real production scraper.
    // This check makes no external HTTP requests or database changes.
    $scraper = (new WebScraperHttp)->setBody($fixture['html']);
    $raw = StrategyExtractor::extract($scraper, $strategy, 'availability');
    checkSame($raw, $fixture['raw'], $fixture['name'].' attribute extraction');
    $status = StockStatus::resolveAvailability($raw, $strategy);
    checkSame($status->value, $fixture['status'], $fixture['name'].' native stock status');
    printf("PASS %s => %s\n", $fixture['name'], $status->value);
}

// A missing value is handled before the default, even with another default.
$otherDefault = $config;
$otherDefault['match']['default'] = 'out_of_stock';
$otherStrategy = AvailabilityStrategyDto::fromArray($otherDefault);
$missing = StrategyExtractor::extract((new WebScraperHttp)->setBody('<p>No marker</p>'), $otherStrategy, 'availability');
checkSame($missing, null, 'missing marker extraction');
checkSame(StockStatus::resolveAvailability($missing, $otherStrategy)->value, 'in_stock', 'native missing-value behavior precedes default');
echo "PASS missing marker still resolves in_stock with default out_of_stock\n";

echo 'PASS '.count($fixtures)." complete native extraction/status cases and missing-value default check\n";
