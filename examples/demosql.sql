CREATE TABLE triples (
    subject TEXT,
    predicate TEXT,
    object TEXT
);

INSERT INTO triples VALUES ("john", "parent", "douglas");
INSERT INTO triples VALUES ("bob", "parent", "john");
INSERT INTO triples VALUES ("ebbon", "parent", "bob");

-- Create index to match caching strategy
CREATE INDEX triples_subject ON triples(subject);
