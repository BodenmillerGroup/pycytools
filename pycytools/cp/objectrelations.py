from pycytools.cp.vars import RELATIONSHIP, FIRST_OBJ_NAME, SECOND_OBJ_NAME, FIRST_OBJ_NUMBER, SECOND_OBJ_NUMBER, \
    FIRST_IMG_NUMBER, SECOND_IMG_NUMBER, OBJ_NUMBER, IMG_NUMBER, OBJ_ID, NEIGHBORS, CHILD, PARENT


class ObjectRelations:

    def __init__(self, dat_obj_rel):
        self.relations = {}
        grp_vars = [RELATIONSHIP,
                    FIRST_OBJ_NAME,
                    SECOND_OBJ_NAME]
        for (rel, f, s), d in (dat_obj_rel
                .groupby(grp_vars,
                         sort=False, as_index=False)):
            rel_dict = self.relations.get(rel, {})
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

    def get_vars_via_rel(self, rel, value_vars, objectname_1, dat_1, objectname_2=None, dat_2=None):
        if rel == NEIGHBORS:
            assert (objectname_2 is None) or (objectname_2 == objectname_1), f'Objectnames need to agree for {rel}'
        if objectname_2 is None:
            objectname_2 = objectname_1
        if dat_2 is None:
            dat_2 = dat_1

        dat_rel = self.relations[rel][objectname_1][objectname_2]

        dat_merged = (dat_1[[OBJ_NUMBER, IMG_NUMBER]].reset_index(drop=False)
                      .merge(dat_rel, left_on=[OBJ_NUMBER, IMG_NUMBER],
                             right_on=[FIRST_OBJ_NUMBER, FIRST_IMG_NUMBER])
                      .dropna()
                      .drop(columns=[OBJ_NUMBER, IMG_NUMBER,
                                     FIRST_OBJ_NUMBER, FIRST_IMG_NUMBER])
                      .merge(dat_2[[OBJ_NUMBER, IMG_NUMBER, *value_vars]],
                             right_on=[OBJ_NUMBER, IMG_NUMBER],
                             left_on=[SECOND_OBJ_NUMBER, SECOND_IMG_NUMBER])
                      .drop(columns=[OBJ_NUMBER, IMG_NUMBER, SECOND_OBJ_NUMBER, SECOND_IMG_NUMBER])
                      .set_index(OBJ_ID)
                      )
        return dat_merged
