"""Character sheets for the Pendragon 6th edition."""
from typing import Optional, List, Set

from pydantic import Field, model_validator
from pydantic.main import BaseModel

from .base import Character


class Checkable(BaseModel):
    """Base class for parts of the character sheet that are checkable"""

    checks: Set[str] = Field(default_factory=set, description='Scores which have had a critical success this season')


class HasExtras(Checkable, extra='allow'):
    """Base class for which allows custom, checkable scores are allowed"""

    @model_validator(mode='after')
    def _extras_are_ints(self):
        for k, v in self.model_extra.items():
            if not isinstance(v, int):
                raise ValueError(f'All extra traits must be ints. {k} is a {type(v)}')
        return self


class Traits(HasExtras):
    """Personality traits for a character

    Only the "virtuous traits" are defined by a user. The "negative" ones are derived."""

    # Core trait values
    chaste: int = Field(..., description='Attitude towards carnal pleasure and romantic fidelity', gt=0)
    energetic: int = Field(..., description='Behaviors related to activity and inactivity', gt=0)
    forgiving: int = Field(..., description='Whether revenge is an acceptable pathway to justice', gt=0)
    generous: int = Field(..., description='Willingness to share or not share with others', gt=0)
    honest: int = Field(..., description='How much they are willing to bend truth to their own needs', gt=0)
    just: int = Field(..., description='Whether they believe laws govern all people', gt=0)
    merciful: int = Field(..., description='An innate sense (or lack) of regard to others', gt=0)
    modest: int = Field(..., description='How much a person thinks of themselves in comparison to others', gt=0)
    prudent: int = Field(..., description='How much a person thinks before acting', gt=0)
    spiritual: int = Field(..., description='A character\'s attitude toward and faith in the unseen world.', gt=0)
    temperate: int = Field(..., description='A character\'s appetite for good food and drink.', gt=0)
    trusting: int = Field(..., description='The level of faith a person places '
                                           'in the motivations and intentions of others', gt=0)
    valorous: int = Field(..., description='How brave and audacious a character may be during times of extreme duress',
                          gt=0)

    # TODO (wardlt): Allow for directed traits

    # Derived traits
    @property
    def lustful(self) -> int:
        """Attitude towards carnal pleasure and romantic fidelity"""
        return 20 - self.chaste

    @property
    def lazy(self) -> int:
        """Behaviors related to activity and inactivity"""
        return 20 - self.energetic

    @property
    def vengeful(self) -> int:
        """Whether revenge is an acceptable pathway to justice"""
        return 20 - self.forgiving

    @property
    def selfish(self) -> int:
        """Willingness to share or not share with others"""
        return 20 - self.generous

    @property
    def deceitful(self) -> int:
        """How much they are willing to bend truth to their own needs"""
        return 20 - self.honest

    @property
    def arbitrary(self) -> int:
        """Whether they believe laws govern all people"""
        return 20 - self.just

    @property
    def cruel(self) -> int:
        """An innate sense (or lack) of regard for others"""
        return 20 - self.merciful

    @property
    def proud(self) -> int:
        """How much a person thinks of themselves in comparison to others"""
        return 20 - self.modest

    @property
    def reckless(self) -> int:
        """How much a person thinks before acting"""
        return 20 - self.prudent

    @property
    def worldly(self) -> int:
        """A character's attitude toward and faith in the unseen world"""
        return 20 - self.spiritual

    @property
    def indulgent(self) -> int:
        """A character's appetite towards good food and drink"""
        return 20 - self.temperate

    @property
    def suspicious(self) -> int:
        """The level of faith a person places in the motivations and intentions of others"""
        return 20 - self.trusting

    @property
    def cowardly(self) -> int:
        """How brave and audacious a character may be during times of extreme duress"""
        return 20 - self.valorous

    @property
    def chivalry_bonus(self):
        return self.energetic + self.generous + self.just + self.merciful + self.modest + self.valorous

    def get_religious_bonus(self, religion: str) -> int:
        """Compute the religious bonus given religion"""

        religion = religion.lower()
        if religion == 'christian':
            return self.chaste + self.forgiving + self.merciful + self.modest + self.temperate + self.spiritual
        elif religion == 'pagan':
            return self.energetic + self.generous + self.honest + self.lustful + self.proud + self.spiritual
        elif religion == 'wodinic':
            return self.generous + self.indulgent + self.proud + self.reckless + self.valorous + self.worldly
        else:
            raise NotImplementedError(f'No such religion: {religion}')


class Passions(HasExtras):
    """What drives the knight's decisions

    Knights only have a few passions and can pull from them to perform heroic deeds.
    """

    homage: Optional[int] = Field(None, description='A knight swears service to a lord')
    fealty: Optional[int] = Field(None, description='A knight makes a lesser oath of loyalty')
    loyalty_companions: Optional[int] = Field(None, description='A knight bonds to his compatriots')
    loyalty_king: Optional[int] = Field(None, description='A knight supports his land\'s ruler.')

    hate: Optional[int] = Field(None, description='A knight is driven by a bitter poison')
    love_family: Optional[int] = Field(None, description='A knight protects those who share his blood.')
    love_person: Optional[int] = Field(None, description='A knight has fervor for a specific individual')

    adoration: Optional[int] = Field(None, description='A knight is commanded by admiration for a Beloved.')
    devotion: Optional[int] = Field(None, description='A knight follows a faith in the supernatural.')

    chivalry: Optional[int] = Field(None, description='A knight believes he must protect the weak')
    hospitality: Optional[int] = Field(None, description='A knight provides for and protects visitors')
    station: Optional[int] = Field(None, description='A knight is above the common but below the lords')

    details: List[str] = Field(default_factory=list, description='Record notes about the passions')

    checks: Set[str] = Field(default_factory=set, description='Passions that have been checked this season')


class Statistics(Checkable):
    """Physical traits of the character"""

    siz: int = Field(..., description='Size and weight compared to others. Also the knockdown modifier')
    dex: int = Field(..., description='Agility and nimbleness')
    str: int = Field(..., description='Physical power')
    con: int = Field(..., description='Health and vitality')
    app: int = Field(..., description='Natural charm, presence, and physical attractiveness')

    @property
    def damage(self) -> int:
        """Modifier to damage.

        Number of d6 rolled with a weapon, and the flat damage when brawling"""
        return (self.str + self.siz) // 6

    @property
    def healing_rate(self):
        """Number of hit points healed per week"""
        return self.con // 5

    @property
    def move_rate(self):
        """Speed of the character. (Feet per round?)"""
        return (self.str + self.dex) // 2 + 5

    @property
    def hit_point_max(self):
        """Number of hit points when fully healthy"""
        return self.siz + self.con

    @property
    def unconscious(self):
        """A character loses consciousness if hit points are below this value"""
        return self.hit_point_max // 4

    @property
    def major_wound(self):
        """Threshold for damage in a single attack

        A character loses consciousness and receives a Major Wound if they
        take this much damage in a single round"""
        return self.con


class Skills(HasExtras):
    """Proficiency at specific actions"""

    # Combat-oriented
    battle: int = Field(..., description='Survive and lead in large-scale military conflict')
    siege: int = Field(..., description='Overcoming the defenses of a stronghold')
    horsemanship: int = Field(..., description='Guiding horses through difficult circumstances')

    # Weapons
    sword: int = Field(..., description='Wielding swords')
    lance: int = Field(..., description='Wielding a lance while mounted')
    spear: int = Field(..., description='Fighting with a polearm')
    dagger: int = Field(..., description='Using a small knife in battle')

    # Other
    awareness: int = Field(..., description='Attentiveness and ability to use their senses')
    boating: int = Field(..., description='Being useful on watercraft')
    compose: int = Field(..., description='Preparing a speech or work of musical art')
    courtesy: int = Field(..., description='Knowledge of culture, laws, and customs of the noble class')
    dancing: int = Field(..., description='Demonstrating grace on the dance floor')
    faerie_lore: int = Field(..., description='Knowledge of the unseen world')
    fashion: int = Field(..., description='Expressing themselves with garments')
    first_aid: int = Field(..., description='Providing immediate medical assistance')
    flirting: int = Field(..., description='Communicating charm and gaining someone\'s interest')
    folklore: int = Field(..., description='Knowledge of the culture, laws, and customs of the common class')
    gaming: int = Field(..., description='Ability with amusements for either competition or entertainment')
    heraldry: int = Field(..., description='Recognizing the markings of specific noble groups')
    hunting: int = Field(..., description='Tracking, traveling in wilds, and concealing one\'s trail')
    intrigue: int = Field(..., description='Learning and spreading secrets in court')
    orate: int = Field(..., description='Influence others with well-delivered words')
    recognize: int = Field(..., description='Remember and identify specific people')
    romance: int = Field(..., description='Establishing long term courtship')
    singing: int = Field(..., description='Delivering beautiful music without an instrument')
    stewardship: int = Field(..., description='Understanding how to manage land')
    swimming: int = Field(..., description='Moving about in water without a boat')
    tourney: int = Field(..., description='Knowing the routine and intricacies of noble competition')


class PendragonCharacter(Character):
    """Character sheet for the Pendragon system"""

    # Basic details
    age: int = Field(..., description='Age of the knight', gt=0)
    son_number: int = Field(..., description='How far the knight is from inheritance.')
    homeland: str = Field(..., description='Where the knight is from')
    culture: Optional[str] = Field(None, description='Culture within the homeland')
    lord: Optional[str] = Field(None, description='With whom they pledged fealty')
    current_class: str = Field(..., description='Knightly occupation')
    current_home: str = Field(..., description='Where they are when not traveling')
    distinctive_features: List[str] = Field(default_factory=list,
                                            description='Easy ways of telling them apart visually')
    hit_points: Optional[None] = Field(None, description='Current level of health')
    glory: int = Field(0, description='How much reknown the character has acquired')

    @property
    def glory_roll(self) -> int:
        return int(round(self.glory / 1000., 0))

    # Personality Traits
    traits: Traits = Field(..., description='Personality traits')
    passions: Passions = Field(..., description='Driving passions')
    statistics: Statistics = Field(..., description='Physical characteristics')
