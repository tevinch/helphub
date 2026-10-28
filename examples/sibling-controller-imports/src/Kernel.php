<?php
namespace App;

use Guide\ApiGrid\ApiGridBundle;
use Guide\Grid\GridBundle;
use Symfony\Bundle\FrameworkBundle\FrameworkBundle;
use Symfony\Bundle\FrameworkBundle\Kernel\MicroKernelTrait;
use Symfony\Bundle\TwigBundle\TwigBundle;
use Symfony\Component\DependencyInjection\Loader\Configurator\ContainerConfigurator;
use Symfony\Component\HttpKernel\Kernel as BaseKernel;
use Symfony\Component\Routing\Loader\Configurator\RoutingConfigurator;
use Symfony\UX\StimulusBundle\StimulusBundle;

final class Kernel extends BaseKernel
{
    use MicroKernelTrait;

    public function registerBundles(): iterable
    {
        yield new FrameworkBundle();
        yield new TwigBundle();
        yield new StimulusBundle();
        yield new GridBundle();
        yield new ApiGridBundle();
    }

    public function getProjectDir(): string
    {
        return dirname(__DIR__);
    }

    protected function configureContainer(ContainerConfigurator $container): void
    {
        $container->extension('framework', [
            'secret' => 'local-example',
            'router' => ['utf8' => true],
            'asset_mapper' => [
                'paths' => [
                    '%kernel.project_dir%/assets' => '',
                    '%kernel.project_dir%/node_modules/@hotwired/stimulus/dist' => '@hotwired/stimulus',
                ],
                'importmap_polyfill' => false,
            ],
        ]);
        $container->extension('twig', [
            'default_path' => '%kernel.project_dir%/templates',
            'strict_variables' => true,
        ]);
        $container->services()->set(PageController::class)->public()->autowire()->autoconfigure();
    }

    protected function configureRoutes(RoutingConfigurator $routes): void
    {
        $routes->add('home', '/')->controller(PageController::class);
    }
}
