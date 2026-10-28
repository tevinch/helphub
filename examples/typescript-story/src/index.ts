import type { Story, StoryConfig } from '@sharpee/sharpee';
import {
  ActorTrait,
  EntityType,
  Direction,
  IdentityTrait,
  RoomTrait,
} from '@sharpee/world-model';
import type { IFEntity, WorldModel } from '@sharpee/world-model';

const config: StoryConfig = {
  id: 'quiet-study',
  title: 'Quiet Study',
  authors: ['Tevinch'],
  version: '1.0.0',
  description: 'An editable TypeScript story with two rooms and a key.',
};

export function createStory(): Story {
  // Keep mutable state inside this factory so each new game starts fresh.
  let player: IFEntity | undefined;

  return {
    config,

    initializeWorld(world: WorldModel): void {
      const study = world.createEntity('Study', EntityType.ROOM);
      study.add(new IdentityTrait({
        name: 'Study',
        description: 'A quiet study. A doorway leads north to the hall.',
      }));

      const hall = world.createEntity('Hall', EntityType.ROOM);
      hall.add(new IdentityTrait({
        name: 'Hall',
        description: 'Sunlight fills the hall. The study is to the south.',
      }));

      study.add(new RoomTrait({ exits: { [Direction.NORTH]: { destination: hall.id } } }));
      hall.add(new RoomTrait({ exits: { [Direction.SOUTH]: { destination: study.id } } }));

      const key = world.createEntity('brass key', EntityType.ITEM);
      key.add(new IdentityTrait({ name: 'brass key', description: 'A small brass key.' }));
      world.moveEntity(key.id, study.id);

      player = world.createEntity('you', EntityType.ACTOR);
      player.add(new IdentityTrait({ name: 'you', description: 'An adventurer.' }));
      player.add(new ActorTrait({ isPlayable: true }));
      world.moveEntity(player.id, study.id);
    },

    // In 5.5.0 the engine builds the world first, then asks for its player.
    createPlayer(): IFEntity {
      if (!player) throw new Error('The world must be initialized before selecting its player.');
      return player;
    },
  };
}
