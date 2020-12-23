from pycytools.cp.vars import RELATIONSHIP, FIRST_OBJ_NAME, SECOND_OBJ_NAME, FIRST_OBJ_NUMBER, SECOND_OBJ_NUMBER, \
    FIRST_IMG_NUMBER, SECOND_IMG_NUMBER, OBJ_NUMBER, IMG_NUMBER, OBJ_ID, NEIGHBORS, CHILD, PARENT


def strip_column_names(dat):
    dat.columns = map(lambda x: x.replace(' ', ''), dat.columns)


class ObjectRelations:

    def __init__(self, dat_obj_rel):
        self.relations = {}
        strip_column_names(dat_obj_rel)
        for rel, d in (dat_obj_rel
                .groupby(RELATIONSHIP,
                         sort=False, as_index=False)):
            dat = d.drop(columns=RELATIONSHIP)
            self.add_relationship(rel, dat)

    def add_relationship(self, rel, dat):
        rel_dict = self.relations.get(rel, {})
        grp_vars = [FIRST_OBJ_NAME,
                    SECOND_OBJ_NAME]
        for (f, s), d in (dat
                .groupby(grp_vars,
                         sort=False,
                         as_index=False)):
            dic = rel_dict.get(f, {})
            dic[s] = d.drop(columns=grp_vars)
            rel_dict[f] = dic
        self.relations[rel] = rel_dict

    @property
    def child(self):
        return self.relations[CHILD]

    @property
    def parent(self):
        return self.relations[PARENT]

    @property
    def neighbors(self):
        return self.relations[NEIGHBORS]

    def get_vars_via_rel(self, rel, value_vars, objectname_1, dat_1, objectname_2=None, dat_2=None,
                         rel_vars=None):
        """
        Add variables via relation
        :params rel: relationship name
        :params value_vars: variables from dat_2 to append to dat_1
        :params objectname_1: name of object_1
        :params dat_1: dataframe to receive appended columns
        :params objectname_2: name of object_2
        :params dat_2: dataframe to get columns from
        """
        if rel == NEIGHBORS:
            assert (objectname_2 is None) or (objectname_2 == objectname_1), f'Objectnames need to agree for {rel}'
        if objectname_2 is None:
            objectname_2 = objectname_1
        if dat_2 is None:
            dat_2 = dat_1

        dat_rel = self.relations[rel][objectname_1][objectname_2]
        if rel_vars is None:
            rel_vars = []
        cols = [FIRST_OBJ_NUMBER, FIRST_IMG_NUMBER,
                SECOND_OBJ_NUMBER, SECOND_IMG_NUMBER
                ]
        dat_rel = dat_rel[list(set(cols + rel_vars))]

        dat_merged = (dat_1[[OBJ_NUMBER, IMG_NUMBER]].reset_index(drop=False)
                      .merge(dat_rel, left_on=[OBJ_NUMBER, IMG_NUMBER],
                             right_on=[FIRST_OBJ_NUMBER, FIRST_IMG_NUMBER])
                      .dropna()
                      .drop(columns=
                            list({OBJ_NUMBER, IMG_NUMBER, FIRST_OBJ_NUMBER, FIRST_IMG_NUMBER} - set(rel_vars)))
                      .merge(dat_2[[OBJ_NUMBER, IMG_NUMBER, *value_vars]],
                             right_on=[OBJ_NUMBER, IMG_NUMBER],
                             left_on=[SECOND_OBJ_NUMBER, SECOND_IMG_NUMBER])
                      .drop(columns=list(
            {OBJ_NUMBER, IMG_NUMBER, SECOND_OBJ_NUMBER, SECOND_IMG_NUMBER} -
            set(rel_vars)))
                      .set_index(OBJ_ID)
                      )
        return dat_merged

    def get_vars_from_rel(self, rel,
                          objectname,
                          dat,
                          value_vars=None,
                          objectname_2=None):
        if rel == NEIGHBORS:
            assert (objectname_2 is None) or (objectname_2 == objectname_1), f'Objectnames need to agree for {rel}'
        if objectname_2 is None:
            objectname_2 = objectname

        dat_rel = self.relations[rel][objectname][objectname_2]
        if value_vars is not None:
            dat_rel = dat_rel[[FIRST_OBJ_NUMBER, FIRST_IMG_NUMBER,
                               SECOND_OBJ_NUMBER] +
                              value_vars]

        dat_merged = (dat[[OBJ_NUMBER, IMG_NUMBER]]
                      .reset_index(drop=False)
                      .merge(dat_rel, left_on=[OBJ_NUMBER, IMG_NUMBER],
                             right_on=[FIRST_OBJ_NUMBER, FIRST_IMG_NUMBER])
                      .dropna()
                      .set_index(OBJ_ID)
                      )
        return dat_merged
