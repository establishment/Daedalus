class Graph:
    def __init__(self):
        self.name_to_id = {}
        self.id_to_name = {}
        self.node_count = 0
        self.adj_list = {}
        self.inv_adj_list = {}
        self.dfs_current_run = 0

        self.visited = {}
        self.dfs_current_path = []

    def add_node(self, node):
        node = node.upper()
        if node not in self.name_to_id:
            self.node_count += 1
            self.name_to_id[node] = self.node_count
            self.id_to_name[self.node_count] = node
        return self.name_to_id[node]

    def get_node_id(self, node):
        node = node.upper()
        if node not in self.name_to_id:
            return -1
        return self.name_to_id[node]

    def node_id_to_name(self, node_id):
        if node_id in self.id_to_name:
            return self.id_to_name[node_id]
        return None

    def add_edge(self, from_node, to_node):
        from_node_id = self.add_node(from_node)
        to_node_id = self.add_node(to_node)
        if from_node_id not in self.adj_list:
            self.adj_list[from_node_id] = set()
        self.adj_list[from_node_id].add(to_node_id)
        if to_node_id not in self.inv_adj_list:
            self.inv_adj_list[to_node_id] = set()
        self.inv_adj_list[to_node_id].add(from_node_id)

    def exists_node(self, node):
        return self.get_node_id(node) != 0

    def exists_edge(self, from_node, to_node):
        from_node_id = self.get_node_id(from_node)
        if from_node_id == -1:
            return False

        to_node_id = self.get_node_id(to_node)
        if to_node_id == -1:
            return False

        if from_node_id not in self.adj_list:
            return False
        if to_node_id not in self.adj_list[from_node_id]:
            return False
        return True

    def remove_edge(self, from_node, to_node):
        from_node_id = self.get_node_id(from_node)
        if from_node_id == -1:
            return

        to_node_id = self.get_node_id(to_node)
        if to_node_id == -1:
            return

        if from_node_id in self.adj_list:
            self.adj_list[from_node_id].remove(to_node_id)
        if to_node_id in self.inv_adj_list:
            self.inv_adj_list[to_node_id].remove(from_node_id)

    def remove_all_edges(self, node):
        node_id = self.get_node_id(node)
        if node_id == -1:
            return
        if node_id not in self.adj_list:
            return
        for other_node_id in self.adj_list[node_id]:
            self.inv_adj_list[other_node_id].remove(node_id)
        self.adj_list[node_id] = set()

    def _dfs_check_for_cycle(self, node_id):
        self.dfs_current_path.append(self.id_to_name[node_id])
        self.visited[node_id] = self.dfs_current_run
        if node_id in self.adj_list:
            for neighbour_node_id in self.adj_list[node_id]:
                if neighbour_node_id in self.visited:
                    if self.dfs_current_run != self.visited[neighbour_node_id]:
                        return True
                elif self._dfs_check_for_cycle(neighbour_node_id):
                    return True
        self.dfs_current_path.pop()
        return False

    def check_for_cycle(self):
        self.dfs_current_run = 0
        for node_name, node_id in self.name_to_id.items():
            self.visited = {}
            self.dfs_current_path = []
            self.dfs_current_run += 1
            if self._dfs_check_for_cycle(node_id):
                return self.dfs_current_path
        return []

    def _dfs_topo_sort(self, node_id):
        queue = []
        queue.insert(0, node_id)
        self.visited[node_id] = 1
        while queue:
            node_id = queue.pop()
            self.dfs_current_path.append(self.id_to_name[node_id])
            if node_id in self.inv_adj_list:
                for neighbour_node_id in self.inv_adj_list[node_id]:
                    if neighbour_node_id not in self.visited:
                        self.visited[neighbour_node_id] = 1
                        queue.insert(0, neighbour_node_id)

    def topo_sort(self, node):
        node_id = self.get_node_id(node)
        if node_id == -1:
            return []
        self.visited = {}
        self.dfs_current_path = []
        self._dfs_topo_sort(node_id)
        return self.dfs_current_path

    def topo_sort_all(self):
        self.visited = {}
        result = []
        for node_id in self.id_to_name:
            if node_id not in self.visited:
                self.dfs_current_path = []
                self._dfs_topo_sort(node_id)
                self.dfs_current_path.reverse()
                result.extend(self.dfs_current_path)
        return result
