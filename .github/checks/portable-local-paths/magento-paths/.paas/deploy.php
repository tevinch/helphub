<?php

namespace Deployer;

import(__DIR__ . '/deploy.maml');

task('paths:show', function () {
    writeln(json_encode([
        'task' => 'paths:show',
        'deploy_path' => get('deploy_path'),
        'current_path' => get('current_path'),
        'recipes' => get('recipes', []),
    ], JSON_THROW_ON_ERROR));
});
