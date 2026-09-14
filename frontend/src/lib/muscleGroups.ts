/** Public muscle-group tree for kho bài tập filters. */



export type MuscleParentKey =

  | "chest"

  | "back"

  | "shoulders"

  | "arms"

  | "core"

  | "legs"

  | "cardio"

  | "stretch";



export type MuscleTreeGroup = {

  key: MuscleParentKey | string;

  label: string;

  slugs: string[];

  childLabels: Record<string, string>;

};



export type MuscleTreeNodeApi = {

  key: string;

  label_vi: string;

  id?: number | null;

  name_en?: string | null;

  is_filter_only?: boolean;

  children?: MuscleTreeNodeApi[];

};




/** Static fallback when API tree is unavailable. */

export const DEFAULT_MUSCLE_TREE: MuscleTreeGroup[] = [

  {

    key: "chest",

    label: "Ngực",

    slugs: ["chest-upper", "chest-mid", "chest-lower"],

    childLabels: {

      "chest-upper": "Ngực trên",

      "chest-mid": "Ngực giữa",

      "chest-lower": "Ngực dưới",

    },

  },

  {

    key: "back",

    label: "Lưng",

    slugs: ["back-lats", "back-middle", "back-lower"],

    childLabels: {

      "back-lats": "Xô (lat)",

      "back-middle": "Lưng giữa",

      "back-lower": "Thắt lưng",

    },

  },

  {

    key: "shoulders",

    label: "Vai",

    slugs: ["shoulders-front", "shoulders-lateral", "shoulders-rear", "shoulders-traps"],

    childLabels: {

      "shoulders-front": "Vai trước",

      "shoulders-lateral": "Vai giữa",

      "shoulders-rear": "Vai sau",

      "shoulders-traps": "Cầu vai",

    },

  },

  {

    key: "arms",

    label: "Tay",

    slugs: ["biceps", "triceps", "forearms"],

    childLabels: {

      biceps: "Tay trước",

      triceps: "Tay sau",

      forearms: "Cẳng tay",

    },

  },

  {

    key: "core",

    label: "Bụng",

    slugs: ["core-upper", "core-lower", "core-obliques"],

    childLabels: {

      "core-upper": "Bụng trên",

      "core-lower": "Bụng dưới",

      "core-obliques": "Nghiêng (oblique)",

    },

  },

  {

    key: "legs",

    label: "Chân",

    slugs: ["quads", "hamstrings", "glutes", "calves"],

    childLabels: {

      quads: "Đùi trước",

      hamstrings: "Đùi sau",

      glutes: "Mông",

      calves: "Bắp chân",

    },

  },

  { key: "cardio", label: "Cardio", slugs: ["cardio"], childLabels: { cardio: "Cardio" } },

  { key: "stretch", label: "Giãn cơ", slugs: ["stretch"], childLabels: { stretch: "Giãn cơ" } },

];



let _cachedTree: MuscleTreeGroup[] = DEFAULT_MUSCLE_TREE;



export function setMuscleTree(tree: MuscleTreeGroup[]): void {

  _cachedTree = tree.length ? tree : DEFAULT_MUSCLE_TREE;

}



export function getMuscleTree(): MuscleTreeGroup[] {

  return _cachedTree;

}




function buildChildToParent(tree: MuscleTreeGroup[]): Map<string, MuscleTreeGroup> {

  const map = new Map<string, MuscleTreeGroup>();

  for (const group of tree) {

    for (const slug of group.slugs) map.set(slug, group);

  }

  return map;

}



let _childToParent = buildChildToParent(DEFAULT_MUSCLE_TREE);



export function rebuildMuscleTreeMaps(tree: MuscleTreeGroup[]): void {

  _childToParent = buildChildToParent(tree);

}



export function muscleTreeFromApi(nodes: MuscleTreeNodeApi[]): MuscleTreeGroup[] {

  const out: MuscleTreeGroup[] = [];

  for (const node of nodes) {

    const children = node.children || [];

    if (!children.length) {

      out.push({

        key: node.key,

        label: node.label_vi,

        slugs: [node.key],

        childLabels: { [node.key]: node.label_vi },

      });

      continue;

    }

    const childLabels: Record<string, string> = {};

    const slugs: string[] = [];

    for (const c of children) {

      childLabels[c.key] = c.label_vi;

      slugs.push(c.key);

    }

    out.push({

      key: node.key,

      label: node.label_vi,

      slugs,

      childLabels,

    });

  }

  return out;

}



/** Badge / detail: "Ngực · Ngực trên" when the parent has several parts. */

export function muscleDisplayLabel(slug: string, fallback?: string): string {

  const group = _childToParent.get(slug);

  if (!group) return fallback || slug;

  const child = group.childLabels[slug] || fallback || slug;

  if (group.slugs.length <= 1) return group.label;

  return `${group.label} · ${child}`;

}



export function toggleMuscleIds(prev: number[], ids: number[]): number[] {

  if (!ids.length) return prev;

  const allOn = ids.every((id) => prev.includes(id));

  if (allOn) return prev.filter((id) => !ids.includes(id));

  return [...new Set([...prev, ...ids])];

}
