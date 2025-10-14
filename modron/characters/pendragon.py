"""Character sheets for the Pendragon 6th edition."""
from typing import Optional, List, Set

from pydantic import Field, Extra
from pydantic.main import BaseModel

from .base import Character


class Traits(BaseModel):
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

    checks: Set[str] = Field(default_factory=set, description='Traits which have been checked in the current season')

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


class Passions(BaseModel, extra=Extra.allow):
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

    # Personality Traits
    traits: Traits = Field(..., description='Personality traits')
    passions: Passions = Field(..., description='Driving passions')
