# Copyright 2017 Kensho Technologies, Inc.
CREATE CLASS CharacterOrHouse EXTENDS V ABSTRACT
CREATE PROPERTY CharacterOrHouse.name String
CREATE PROPERTY CharacterOrHouse.alias EmbeddedList String
CREATE PROPERTY CharacterOrHouse.uuid String

CREATE CLASS Character EXTENDS CharacterOrHouse

CREATE CLASS NobleHouse EXTENDS CharacterOrHouse
CREATE PROPERTY NobleHouse.motto EmbeddedList String

CREATE CLASS Region EXTENDS V
CREATE PROPERTY Region.name String
CREATE PROPERTY Region.alias EmbeddedList String
CREATE PROPERTY Region.uuid String

CREATE CLASS Owes_Allegiance_To EXTENDS E
CREATE PROPERTY Owes_Allegiance_To.out Link CharacterOrHouse
CREATE PROPERTY Owes_Allegiance_To.in Link CharacterOrHouse

CREATE CLASS Has_Seat EXTENDS E
CREATE PROPERTY Has_Seat.out Link NobleHouse
CREATE PROPERTY Has_Seat.in Link Region

CREATE CLASS Lives_In EXTENDS E
CREATE PROPERTY Lives_In.out Link Character
CREATE PROPERTY Lives_In.in Link Region

CREATE CLASS Has_Parent_Region EXTENDS E
CREATE PROPERTY Has_Parent_Region.out Link Region
CREATE PROPERTY Has_Parent_Region.in Link Region
