import {useEffect, useState} from 'react';
import {dota2Api} from '../api/dota2Api';
import {HeroResponse, SimpleHero} from '../interfaces/heroInterfaces';

export const useHeroStats = () => {
  const [simpleHeroList, setSimpleHeroList] = useState<SimpleHero[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadHeroes = async () => {
    setIsLoading(true);
    const resp = await dota2Api.get('https://api.opendota.com/api/heroes');
    mapHeroList(resp.data);
  };

  const getImageHero = (npc_name: string) => {
    return `https://api.opendota.com/apps/dota2/images/heroes/${npc_name}_full.png`;
  };

  const mapHeroList = (heroList: HeroResponse[]) => {
    const newHeroList: SimpleHero[] = heroList
      .map(({id, localized_name: name, name: npc_name}) => {
        const nameParts = npc_name.split('_');
        console.log(id);
        let picture = '';
        if (nameParts.length === 4) {
          picture = getImageHero(nameParts.slice(-1).join());
        } else if (nameParts.length === 5) {
          picture = getImageHero(nameParts.slice(-2).join('_'));
        }
        // console.log(name);
        return {id, picture, name};
      })
      .filter(item => item.name !== 'Dawnbreaker');
    setSimpleHeroList([...simpleHeroList, ...newHeroList]);
    setIsLoading(false);
  };

  useEffect(() => {
    loadHeroes();
  }, []);

  return {
    isLoading,
    simpleHeroList,
    loadHeroes,
  };
};
