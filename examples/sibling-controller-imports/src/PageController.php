<?php
namespace App;

use Symfony\Component\HttpFoundation\Response;
use Twig\Environment;

final class PageController
{
    public function __construct(private Environment $twig) {}

    public function __invoke(): Response
    {
        return new Response($this->twig->render('index.html.twig'));
    }
}
