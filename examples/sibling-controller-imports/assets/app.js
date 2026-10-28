import { startStimulusApp } from '@symfony/stimulus-bundle';
import ApiGridController from '@guide/api-grid-bundle/controller';
import GridController from '@guide/grid-bundle/controller';
import { message } from 'existing-module';

const application = startStimulusApp();
application.register('api-grid', ApiGridController);
application.register('grid', GridController);
document.querySelector('[data-testid="existing-content"]').textContent = message;
