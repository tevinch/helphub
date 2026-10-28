<?php
require dirname(__DIR__).'/vendor/autoload.php';

use App\Kernel;
use Symfony\Component\HttpFoundation\Request;

$environment = getenv('APP_ENV') ?: 'dev';
$kernel = new Kernel($environment, $environment !== 'prod');
$request = Request::createFromGlobals();
$response = $kernel->handle($request);
$response->send();
$kernel->terminate($request, $response);
